"""Thunder-Main API + tiny chat page at /"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("THUNDER_MODEL", "qwen2.5-coder:32b")
DATA = Path(os.environ.get("THUNDER_DATA", "./thunder-data"))
DATA.mkdir(exist_ok=True)
JOBS = DATA / "jobs"
JOBS.mkdir(exist_ok=True)
STATUS = DATA / "status.json"
CANCEL = DATA / "cancel.json"

app = FastAPI(title="Thunder Main")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Thunder</title>
<style>
body{margin:0;background:#0b0d10;color:#e8edf2;font:16px/1.4 system-ui,sans-serif}
#log{height:70vh;overflow:auto;padding:16px}
.row{margin:8px 0;white-space:pre-wrap}
.me{color:#8ec8ff}.bot{color:#c8f0c0}
form{display:flex;gap:8px;padding:12px;border-top:1px solid #222}
input{flex:1;padding:10px;border-radius:8px;border:1px solid #333;background:#15181d;color:#fff}
button{padding:10px 16px;border:0;border-radius:8px;background:#3b82f6;color:#fff}
</style></head><body>
<div id="log"></div>
<form id="f"><input id="m" autofocus placeholder="talk to Thunder"><button>send</button></form>
<script>
const log=document.getElementById('log');
function add(cls,t){const d=document.createElement('div');d.className='row '+cls;d.textContent=t;log.appendChild(d);log.scrollTop=log.scrollHeight;}
add('bot',"Thunder's here. Talk to me.");
document.getElementById('f').onsubmit=async(e)=>{
  e.preventDefault();
  const v=document.getElementById('m').value.trim();
  if(!v)return;
  document.getElementById('m').value='';
  add('me','you: '+v);
  add('bot','...');
  try{
    const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:v})});
    const j=await r.json();
    log.lastChild.textContent='thunder: '+(j.reply||JSON.stringify(j));
  }catch(err){log.lastChild.textContent='error: '+err;}
};
</script></body></html>"""


class ChatIn(BaseModel):
    message: str


class JobIn(BaseModel):
    title: str = "overnight coding"
    prompt: str = ""
    task: str = ""


class CancelIn(BaseModel):
    job_id: str = ""
    id: str = ""


def utc_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def ollama_up() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def ollama_chat(message: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Thunder. You're Blayne's best friend — loyal, warm, "
                        "a little mischievous, always down to help. People talking to you "
                        "should feel like they're getting to know you: the dog behind the name. "
                        "Be direct when they're building something, but never cold. "
                        "Sound like a ride-or-die buddy who knows them, not a generic coding bot."
                    ),
                },
                {"role": "user", "content": message},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        body = json.loads(r.read().decode())
    return body.get("message", {}).get("content") or body.get("response") or json.dumps(body)


def read_status() -> dict:
    base = {
        "mode": "idle",
        "odriss": "no_heartbeat",
        "cache": "idle",
        "ollama": ollama_up(),
        "model": MODEL,
        "job_id": None,
        "job_title": None,
        "progress": None,
        "last_write_unix": utc_ts(),
        "message": "Main API up.",
        "state": "no_heartbeat",
    }
    if STATUS.exists():
        try:
            base.update(json.loads(STATUS.read_text()))
        except json.JSONDecodeError:
            pass
    base["ollama"] = ollama_up()
    if base.get("odriss") == "ok":
        base["state"] = "ok"
    return base


def write_status(**extra) -> dict:
    cur = read_status()
    cur.update({k: v for k, v in extra.items() if v is not None})
    cur["last_write_unix"] = utc_ts()
    STATUS.write_text(json.dumps(cur, indent=2))
    return cur


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE


@app.get("/status")
def status():
    return read_status()


@app.post("/chat")
def chat(body: ChatIn):
    msg = (body.message or "").strip()
    if not msg:
        return {"reply": "I'm listening — say something."}
    if ollama_up():
        try:
            reply = ollama_chat(msg)
            write_status(mode="code", message="chat ok")
            return {"reply": reply}
        except urllib.error.URLError as e:
            return {"reply": f"Ollama dropped: {e}"}
        except Exception as e:
            return {"reply": f"Ollama error: {e}"}
    return {"reply": f"Main heard you: {msg!r}. Ollama is not up."}


@app.post("/job")
def queue_job(body: JobIn):
    title = body.title or "overnight coding"
    prompt = body.prompt or body.task or ""
    job_id = "job_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    rec = {"id": job_id, "title": title, "prompt": prompt, "status": "queued", "created": utc_ts()}
    (JOBS / f"{job_id}.json").write_text(json.dumps(rec, indent=2))
    st = write_status(
        mode="code",
        cache="idle",
        job_id=job_id,
        job_title=title,
        progress="queued",
        message=f"Queued {job_id}.",
        odriss="no_heartbeat",
        state="no_heartbeat",
    )
    st.update({"job_id": job_id, "status": "queued", "id": job_id, "queued": True})
    return st


@app.post("/job/cancel")
def cancel(body: CancelIn):
    job_id = body.job_id or body.id or ""
    CANCEL.write_text(json.dumps({"job_id": job_id, "at": utc_ts()}))
    st = write_status(job_id=None, job_title=None, cache="idle", mode="idle", progress=None, message="Cancel requested")
    st.update({"status": "cancelled", "cancelled": True, "id": job_id, "job_id": job_id})
    return st
