"""Thunder-Main API.

Run on Main:
  pip install -r requirements.txt
  uvicorn app:app --host 0.0.0.0 --port 8080

/chat talks to local Ollama if it's up.
If Ollama is down, it still answers so the phone UI works.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
                        "You are Thunder, a local coding and chat agent. "
                        "Be direct. Write working code. One job at a time."
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
    with urllib.request.urlopen(req, timeout=180) as r:
        body = json.loads(r.read().decode())
    return (
        body.get("message", {}).get("content")
        or body.get("response")
        or json.dumps(body)
    )


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


@app.get("/status")
def status():
    return read_status()


@app.post("/chat")
def chat(body: ChatIn):
    msg = (body.message or "").strip()
    if not msg:
        return {"reply": "Say something."}
    if ollama_up():
        try:
            reply = ollama_chat(msg)
            write_status(mode="code", message="chat ok")
            return {"reply": reply}
        except urllib.error.URLError as e:
            return {"reply": f"Ollama reachable then dropped: {e}"}
        except Exception as e:
            return {"reply": f"Ollama error: {e}"}
    return {
        "reply": (
            f"Main heard you: {msg!r}. "
            f"Ollama is not up on {OLLAMA}. "
            f"Start it, then pull {MODEL}."
        )
    }


@app.post("/job")
def queue_job(body: JobIn):
    title = body.title or "overnight coding"
    prompt = body.prompt or body.task or ""
    job_id = "job_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    rec = {
        "id": job_id,
        "title": title,
        "prompt": prompt,
        "status": "queued",
        "created": utc_ts(),
    }
    (JOBS / f"{job_id}.json").write_text(json.dumps(rec, indent=2))
    st = write_status(
        mode="code",
        cache="idle",
        job_id=job_id,
        job_title=title,
        progress="queued",
        message=f"Queued {job_id}. Cache worker not attached yet.",
        odriss="no_heartbeat",
        state="no_heartbeat",
    )
    st.update({"job_id": job_id, "status": "queued", "id": job_id, "queued": True})
    return st


@app.post("/job/cancel")
def cancel(body: CancelIn):
    job_id = body.job_id or body.id or ""
    CANCEL.write_text(json.dumps({"job_id": job_id, "at": utc_ts()}))
    st = write_status(
        job_id=None,
        job_title=None,
        cache="idle",
        mode="idle",
        progress=None,
        message="Cancel requested",
    )
    st.update({"status": "cancelled", "cancelled": True, "id": job_id, "job_id": job_id})
    return st
