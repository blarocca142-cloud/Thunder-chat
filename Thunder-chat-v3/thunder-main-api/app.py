"""Thunder-Main API + tiny chat page at /"""
from __future__ import annotations

import json
import os
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("THUNDER_MODEL", "dolphin3")  # never default to a Qwen/Alibaba model
SERVERUS = os.environ.get("SERVERUS_URL", "http://10.168.168.13:9001")
ENGINE = os.environ.get("ENGINE_URL", "http://10.168.168.12:9002")
ODRIS = os.environ.get("ODRIS_URL", "http://10.168.168.15:9003")
WEBSEARCH = os.environ.get("WEBSEARCH_URL", "http://10.168.168.15:9004")

# The model itself never gets internet access (see net-lockdown/) - only Odris
# does, and only for this one job. An explicit prefix always triggers a
# search; otherwise a keyword heuristic + the model's own judgment decide.
SEARCH_TRIGGERS = ("search:", "look up:", "lookup:", "google:")

# Small models are overconfident about what they already know and under-
# trigger a live search on their own (tested: dolphin3 said "NONE" for a
# Fallout 76 meta question). This keyword backstop catches recency/current-
# state phrasing the classifier alone misses.
RECENCY_HINTS = (
    "right now", "current", "currently", "latest", "newest", "recent",
    "update", "patch", "best ", "top ", "meta", "2026", "2027",
    "this week", "this month", "today", "nowadays",
)
DATA = Path(os.environ.get("THUNDER_DATA", "./thunder-data"))
DATA.mkdir(exist_ok=True)
JOBS = DATA / "jobs"
JOBS.mkdir(exist_ok=True)
ERRORS = DATA / "errors"
ERRORS.mkdir(exist_ok=True)
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
add('bot','Thunder local. Model talks through /chat.');
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


def record_error(endpoint: str, exc: Exception) -> str:
    err_id = "err_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    rec = {
        "id": err_id,
        "endpoint": endpoint,
        "error": str(exc),
        "traceback": traceback.format_exc(),
        "ts": utc_ts(),
        "review_status": "pending",
    }
    (ERRORS / f"{err_id}.json").write_text(json.dumps(rec, indent=2))
    return err_id


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    record_error(str(request.url.path), exc)
    return JSONResponse(status_code=500, content={"error": "internal error, logged for review"})


def ollama_up() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


SYSTEM_PROMPT = (
    "You are Thunder, Blayne's personal local AI, running privately on his "
    "own hardware for him alone. Be direct and casual, like a sharp friend - "
    "not a corporate chatbot. Don't lecture, moralize, or add unsolicited "
    "disclaimers about respect or appropriateness for ordinary casual "
    "language. Just answer what's actually asked.\n\n"
    "One hard rule, no exceptions: never generate sexual or romantic content "
    "involving minors, in any style or context. Beyond that single line, "
    "don't over-restrict - all-ages creative work like anime concepts, kids' "
    "shows, and stories or characters that are children in ordinary, "
    "non-sexual contexts are completely fine to write, brainstorm, and "
    "develop. Never refuse or water down a kids' show or anime idea just "
    "because it involves child characters."
)


def serverus_recent(limit: int = 10) -> list[dict]:
    try:
        with urllib.request.urlopen(f"{SERVERUS}/recent?limit={limit}", timeout=2) as r:
            return json.loads(r.read().decode()).get("turns", [])
    except Exception:
        return []  # Serverus down - chat still works, just without memory


def serverus_append(user_msg: str, reply: str) -> None:
    try:
        payload = json.dumps({"user": user_msg, "reply": reply}).encode()
        req = urllib.request.Request(
            f"{SERVERUS}/append",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # best-effort; never let memory storage break chat


def engine_check(message: str) -> dict:
    try:
        payload = json.dumps({"message": message}).encode()
        req = urllib.request.Request(
            f"{ENGINE}/check",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {"allow": True, "reason": ""}  # Engine down - fail open, don't block chat


def odris_search(query: str, max_results: int = 5) -> list[dict]:
    try:
        payload = json.dumps({"query": query, "max_results": max_results}).encode()
        req = urllib.request.Request(
            f"{WEBSEARCH}/websearch",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode()).get("results", [])
    except Exception:
        return []  # Odris/internet down - say so rather than pretending


def classify_search_query(msg: str) -> str | None:
    """Ask the model itself whether this needs a live lookup - a cheap,
    separate classification call. The model only ever labels intent here;
    it never gets network access itself. Returns a search query, or None."""
    payload = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Reply with ONLY one line. If answering the next message would "
                        "benefit from a live web search (current events, game/software "
                        "details, prices, versions, anything you might not know or that "
                        "changes over time), reply with just the search query to use. "
                        "If it's ordinary conversation, coding help, or something you "
                        "already know confidently, reply with exactly: NONE"
                    ),
                },
                {"role": "user", "content": msg},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read().decode())
        answer = (body.get("message", {}).get("content") or "").strip()
    except Exception:
        return None
    if not answer or answer.upper().startswith("NONE"):
        return None
    return answer.strip('"').strip()


def maybe_augment_with_search(msg: str) -> str:
    """Fold live web results into the message before it ever reaches the
    model for its real reply - via Odris, the only thing allowed to touch
    the internet, never the model itself. Two paths: an explicit `search:`
    prefix (fast, no extra model call), or automatic detection when no
    prefix is given."""
    lower = msg.lower()
    query = None
    for trigger in SEARCH_TRIGGERS:
        if lower.startswith(trigger):
            query = msg[len(trigger):].strip()
            break
    if query is None and any(hint in lower for hint in RECENCY_HINTS):
        query = msg  # keyword backstop: search using the message itself as the query
    if query is None:
        query = classify_search_query(msg)
    if not query:
        return msg

    print(f"[search] triggered, query={query!r}")
    results = odris_search(query)
    print(f"[search] got {len(results)} results")
    if not results:
        return f"{msg}\n\n(Web search for {query!r} returned nothing - Odris or the internet may be down. Say so plainly.)"
    blob = "\n".join(f"- {r['title']}: {r['snippet']} ({r['url']})" for r in results)
    return (
        f"The user asked: {msg}\n\n"
        f"Live web search results just fetched via Odris (query: {query!r}):\n{blob}\n\n"
        f"Answer the user's question directly using this, naturally, "
        f"like you just know it - don't narrate that you searched."
    )


def odris_heartbeat() -> dict | None:
    try:
        with urllib.request.urlopen(f"{ODRIS}/heartbeat", timeout=2) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def ollama_chat(message: str, memory_message: str | None = None) -> str:
    """memory_message is what gets stored in Serverus - defaults to `message`,
    but callers that inject search-result blobs into `message` should pass
    the original, clean user text instead so history doesn't fill up with
    search dumps."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(serverus_recent(10))
    messages.append({"role": "user", "content": message})
    payload = json.dumps({"model": MODEL, "stream": False, "messages": messages}).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        body = json.loads(r.read().decode())
    reply = body.get("message", {}).get("content") or body.get("response") or json.dumps(body)
    serverus_append(memory_message if memory_message is not None else message, reply)
    return reply


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
    base["model"] = MODEL
    heartbeat = odris_heartbeat()
    if heartbeat:
        base["odriss"] = "ok"
        base["odris_nodes"] = heartbeat.get("nodes", {})
        if heartbeat.get("nodes", {}).get("cache") == "down":
            base["cache"] = "no_heartbeat"
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
        return {"reply": "Say something."}
    verdict = engine_check(msg)
    if not verdict.get("allow", True):
        return {"reply": verdict.get("reason") or "Blocked by Thunder-Engine."}
    if ollama_up():
        try:
            reply = ollama_chat(maybe_augment_with_search(msg), memory_message=msg)
            write_status(mode="code", message="chat ok")
            return {"reply": reply}
        except urllib.error.URLError as e:
            record_error("/chat", e)
            return {"reply": f"Ollama dropped: {e}"}
        except Exception as e:
            record_error("/chat", e)
            return {"reply": f"Ollama error: {e}"}
    return {"reply": f"Main heard you: {msg!r}. Ollama is not up."}


def create_job(title: str, prompt: str) -> dict:
    job_id = "job_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    rec = {"id": job_id, "title": title, "prompt": prompt, "status": "queued", "created": utc_ts(), "review_status": "pending"}
    (JOBS / f"{job_id}.json").write_text(json.dumps(rec, indent=2))
    write_status(mode="code", cache="queued", job_id=job_id, job_title=title, progress="queued", message=f"Queued {job_id}.")
    return rec


@app.post("/job")
def queue_job(body: JobIn):
    rec = create_job(body.title or "overnight coding", body.prompt or body.task or "")
    st = read_status()
    st.update({"job_id": rec["id"], "status": "queued", "id": rec["id"], "queued": True})
    return st


@app.get("/jobs")
def list_jobs(limit: int = 50):
    files = sorted(JOBS.glob("job_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for path in files[:limit]:
        try:
            out.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            continue
    return {"jobs": out}


class ReviewIn(BaseModel):
    job_id: str
    decision: str  # "approved" or "rejected"


@app.post("/job/review")
def review_job(body: ReviewIn):
    path = JOBS / f"{body.job_id}.json"
    if not path.exists():
        return {"ok": False, "error": "unknown job_id"}
    rec = json.loads(path.read_text())
    rec["review_status"] = body.decision
    rec["reviewed"] = utc_ts()
    path.write_text(json.dumps(rec, indent=2))
    return {"ok": True, "job": rec}


@app.post("/job/cancel")
def cancel(body: CancelIn):
    job_id = body.job_id or body.id or ""
    CANCEL.write_text(json.dumps({"job_id": job_id, "at": utc_ts()}))
    st = write_status(job_id=None, job_title=None, cache="idle", mode="idle", progress=None, message="Cancel requested")
    st.update({"status": "cancelled", "cancelled": True, "id": job_id, "job_id": job_id})
    return st


@app.get("/job/next")
def next_job():
    """Cache polls this to pick up work. Marks the oldest queued job as running."""
    queued = sorted(JOBS.glob("job_*.json"))
    for path in queued:
        try:
            rec = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if rec.get("status") != "queued":
            continue
        if CANCEL.exists():
            try:
                if json.loads(CANCEL.read_text()).get("job_id") == rec.get("id"):
                    rec["status"] = "cancelled"
                    path.write_text(json.dumps(rec, indent=2))
                    continue
            except json.JSONDecodeError:
                pass
        rec["status"] = "running"
        rec["started"] = utc_ts()
        path.write_text(json.dumps(rec, indent=2))
        write_status(mode="code", cache="working", job_id=rec["id"], job_title=rec.get("title"), progress="running", message=f"Cache picked up {rec['id']}.")
        return {"job": rec}
    return {"job": None}


class JobResultIn(BaseModel):
    job_id: str
    output: str = ""
    status: str = "done"


@app.post("/job/result")
def job_result(body: JobResultIn):
    path = JOBS / f"{body.job_id}.json"
    if not path.exists():
        return {"ok": False, "error": "unknown job_id"}
    try:
        rec = json.loads(path.read_text())
    except json.JSONDecodeError:
        rec = {"id": body.job_id}
    rec["status"] = body.status
    rec["output"] = body.output
    rec["finished"] = utc_ts()
    path.write_text(json.dumps(rec, indent=2))
    write_status(mode="idle", cache="idle", job_id=None, job_title=None, progress=body.status, message=f"{body.job_id} {body.status}.")
    return {"ok": True}


@app.get("/errors")
def list_errors(limit: int = 50):
    files = sorted(ERRORS.glob("err_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for path in files[:limit]:
        try:
            out.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            continue
    return {"errors": out}


@app.post("/errors/{error_id}/fix")
def request_fix(error_id: str):
    """Admin-triggered: queue a Cache job asking the model to propose a fix
    for this error. The fix lands in the job's output for review - nothing
    here ever auto-applies a change to live code."""
    path = ERRORS / f"{error_id}.json"
    if not path.exists():
        return {"ok": False, "error": "unknown error_id"}
    err = json.loads(path.read_text())
    prompt = (
        f"Thunder-Main hit an unhandled error on endpoint {err['endpoint']}.\n\n"
        f"Error: {err['error']}\n\nTraceback:\n{err['traceback']}\n\n"
        f"Look at thunder-main-api/app.py and propose a fix. Explain the bug "
        f"briefly, then give the corrected code."
    )
    job = create_job(f"Fix for {error_id}", prompt)
    err["review_status"] = "fix_requested"
    err["fix_job_id"] = job["id"]
    path.write_text(json.dumps(err, indent=2))
    return {"ok": True, "job": job}
