"""Thunder-Main API stub. Run on Main: uvicorn app:app --host 0.0.0.0 --port 8080

At 12:45 replace chat_reply() with Ollama and queue_job() with a Serverus write.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Point this at Serverus when the mount exists
DATA = Path("./thunder-data")
DATA.mkdir(exist_ok=True)
STATUS = DATA / "status.json"
JOBS = DATA / "jobs"
JOBS.mkdir(exist_ok=True)

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


class CancelIn(BaseModel):
    job_id: str = ""


def now_status(**extra):
    base = {
        "mode": "idle",
        "odriss": "no_heartbeat",
        "cache": "idle",
        "job_id": None,
        "job_title": None,
        "progress": None,
        "last_write_unix": int(datetime.now(timezone.utc).timestamp()),
        "message": "API up. Ollama and Odris not wired yet.",
    }
    if STATUS.exists():
        try:
            base.update(json.loads(STATUS.read_text()))
        except json.JSONDecodeError:
            pass
    base.update({k: v for k, v in extra.items() if v is not None})
    STATUS.write_text(json.dumps(base, indent=2))
    return base


@app.get("/status")
def status():
    return now_status()


@app.post("/chat")
def chat(body: ChatIn):
    # TODO: POST http://127.0.0.1:11434/api/chat
    return {
        "reply": (
            f"Main API heard you: {body.message!r}. "
            "Hook this route to Ollama and I stop being a stub."
        )
    }


@app.post("/job")
def queue_job(body: JobIn):
    job_id = "job_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    path = JOBS / f"{job_id}.json"
    path.write_text(json.dumps({"id": job_id, "title": body.title, "prompt": body.prompt, "status": "queued"}, indent=2))
    return now_status(
        mode="code",
        cache="idle",
        job_id=job_id,
        job_title=body.title,
        message=f"Queued on disk {path}. Cache worker not attached yet.",
        odriss="no_heartbeat",
    ) | {"job_id": job_id, "status": "queued"}


@app.post("/job/cancel")
def cancel(body: CancelIn):
    return now_status(job_id=None, job_title=None, cache="idle", message="Cancel requested") | {
        "status": "cancelled",
        "job_id": body.job_id,
    }
