"""Thunder-Main API. Chat contract stays: POST /chat {message} → {reply}."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import creative

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("THUNDER_MODEL", "qwen2.5-coder:14b")
DATA = Path(os.environ.get("THUNDER_DATA", "./thunder-data"))
DATA.mkdir(exist_ok=True)
JOBS = DATA / "jobs"
JOBS.mkdir(exist_ok=True)
CREATIONS = DATA / "creations"
CREATIONS.mkdir(exist_ok=True)
STATUS = DATA / "status.json"
CANCEL = DATA / "cancel.json"
WEB = Path(__file__).resolve().parent.parent / "thunder-web"
LOGS: deque[dict] = deque(maxlen=200)
SYSTEM = (
    "You are Thunder. You're Blayne's best friend — loyal, warm, "
    "a little mischievous, always down to help. People talking to you "
    "should feel like they're getting to know you: the dog behind the name. "
    "Be direct when they're building something, but never cold. "
    "Sound like a ride-or-die buddy who knows them, not a generic coding bot."
)

app = FastAPI(title="Thunder Main", version="0.7.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatIn(BaseModel):
    message: str = ""
    messages: list[dict] | None = None


class JobIn(BaseModel):
    title: str = "overnight coding"
    prompt: str = ""
    task: str = ""


class CancelIn(BaseModel):
    job_id: str = ""
    id: str = ""


class ImageIn(BaseModel):
    prompt: str
    style: str = "Cinematic"
    aspect: str = "1:1"


class VideoIn(BaseModel):
    prompt: str
    style: str = "Cinematic"
    duration: int = 8


class ModelIn(BaseModel):
    model: str = ""
    name: str = ""


def utc_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def log_event(kind: str, message: str) -> None:
    LOGS.appendleft({"at": utc_ts(), "kind": kind, "message": message})


def ollama_up() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def ollama_tags() -> list[dict]:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=4) as r:
            body = json.loads(r.read().decode())
        return [
            {
                "name": m.get("name", ""),
                "size": m.get("size"),
                "digest": m.get("digest"),
            }
            for m in body.get("models", [])
            if m.get("name")
        ]
    except Exception:
        return []


def ollama_chat(user_text: str, history: list[dict] | None = None) -> str:
    messages = [{"role": "system", "content": SYSTEM}]
    if history:
        for item in history:
            role = item.get("role") or item.get("who")
            content = item.get("content") or item.get("text") or ""
            if role in ("you", "user"):
                role = "user"
            elif role in ("thunder", "assistant", "bot"):
                role = "assistant"
            else:
                continue
            if content:
                messages.append({"role": role, "content": content})
    if user_text:
        messages.append({"role": "user", "content": user_text})
    payload = json.dumps({"model": MODEL, "stream": False, "messages": messages}).encode()
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
        "app_version": "0.7.0",
        "image_hook": bool(creative.IMAGE_HOOK),
        "video_hook": bool(creative.VIDEO_HOOK),
    }
    if STATUS.exists():
        try:
            base.update(json.loads(STATUS.read_text()))
        except json.JSONDecodeError:
            pass
    base["ollama"] = ollama_up()
    base["model"] = MODEL
    base["app_version"] = "0.7.0"
    base["image_hook"] = bool(creative.IMAGE_HOOK)
    base["video_hook"] = bool(creative.VIDEO_HOOK)
    if base.get("odriss") == "ok":
        base["state"] = "ok"
    return base


def write_status(**extra) -> dict:
    cur = read_status()
    cur.update(extra)
    cur["last_write_unix"] = utc_ts()
    STATUS.write_text(json.dumps(cur, indent=2))
    return cur


def web_file(name: str) -> Path:
    path = (WEB / name).resolve()
    if not str(path).startswith(str(WEB.resolve())) or not path.is_file():
        raise HTTPException(404, f"missing {name}")
    return path


@app.get("/", response_class=HTMLResponse)
def home():
    index = WEB / "index.html"
    if index.exists():
        return FileResponse(index)
    return HTMLResponse("<p>Thunder web client is missing.</p>")


@app.get("/status")
def status():
    return read_status()


@app.get("/logs")
def logs():
    return {"lines": list(LOGS)}


@app.get("/models")
def models():
    return {"current": MODEL, "ollama": ollama_up(), "models": ollama_tags()}


@app.post("/model")
def set_model(body: ModelIn):
    global MODEL
    name = (body.model or body.name or "").strip()
    if not name:
        raise HTTPException(400, "model required")
    MODEL = name
    log_event("model", f"model set to {MODEL}")
    write_status(model=MODEL, message=f"Model {MODEL}")
    return {"current": MODEL, "models": ollama_tags()}


@app.post("/chat")
def chat(body: ChatIn):
    msg = (body.message or "").strip()
    history = body.messages
    if not msg and not history:
        return {"reply": "I'm listening — say something."}
    if ollama_up():
        try:
            reply = ollama_chat(msg, history)
            write_status(mode="code", message="chat ok")
            log_event("chat", f"ok ({len(msg)} chars)")
            return {"reply": reply}
        except urllib.error.URLError as e:
            log_event("chat", f"ollama dropped: {e}")
            return {"reply": f"Ollama dropped: {e}"}
        except Exception as e:
            log_event("chat", f"ollama error: {e}")
            return {"reply": f"Ollama error: {e}"}
    log_event("chat", "ollama down — fallback")
    return {"reply": f"Main heard you: {msg!r}. Ollama is not up."}


@app.post("/image")
def make_image(body: ImageIn):
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt required")
    style = body.style or "Cinematic"
    aspect = body.aspect if body.aspect in creative.ASPECTS else "1:1"
    stub = True
    extra = {}
    if creative.IMAGE_HOOK:
        try:
            hooked = creative.forward_hook(
                creative.IMAGE_HOOK,
                {"prompt": prompt, "style": style, "aspect": aspect},
            )
            if hooked.get("bytes"):
                png = hooked["bytes"]
                stub = False
            elif hooked.get("image_b64"):
                import base64

                png = base64.b64decode(hooked["image_b64"])
                stub = False
            else:
                png = creative.render_stub_png(prompt, style, aspect, "image")
                extra["hook"] = hooked
            message = hooked.get("message") or ("Image hook returned a still." if not stub else "Hook did not return image bytes; stub used.")
        except Exception as e:
            png = creative.render_stub_png(prompt, style, aspect, "image")
            message = f"Image hook failed ({e}); stub still saved."
            extra["hook_error"] = str(e)
    else:
        png = creative.render_stub_png(prompt, style, aspect, "image")
        message = "Studio stub. Point THUNDER_IMAGE_URL at a generator when you have one."
    item = creative.record(
        creations_dir=CREATIONS,
        kind="image",
        prompt=prompt,
        style=style,
        aspect=aspect,
        png=png,
        stub=stub,
        message=message,
        extra=extra,
    )
    log_event("image", f"{item['id']} stub={stub}")
    write_status(mode="studio", message=f"image {item['id']}")
    return item


@app.post("/video")
def make_video(body: VideoIn):
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt required")
    style = body.style or "Cinematic"
    duration = max(3, min(int(body.duration or 8), 30))
    stub = True
    extra = {"duration": duration, "video_url": None}
    if creative.VIDEO_HOOK:
        try:
            hooked = creative.forward_hook(
                creative.VIDEO_HOOK,
                {"prompt": prompt, "style": style, "duration": duration},
            )
            extra["hook"] = {k: hooked[k] for k in hooked if k != "bytes"}
            if hooked.get("video_url"):
                extra["video_url"] = hooked["video_url"]
                stub = False
            message = hooked.get("message") or "Video hook accepted the job."
        except Exception as e:
            message = f"Video hook failed ({e}); poster stub saved."
            extra["hook_error"] = str(e)
        png = creative.render_stub_png(prompt, style, "16:9", "video")
    else:
        png = creative.render_stub_png(prompt, style, "16:9", "video")
        message = (
            f"Motion stub ({duration}s). Set THUNDER_VIDEO_URL to plug a renderer. "
            "The poster is in history until that hook exists."
        )
    item = creative.record(
        creations_dir=CREATIONS,
        kind="video",
        prompt=prompt,
        style=style,
        aspect="16:9",
        duration=duration,
        png=png,
        stub=stub,
        message=message,
        extra=extra,
    )
    log_event("video", f"{item['id']} stub={stub} {duration}s")
    write_status(mode="studio", message=f"video {item['id']}")
    return item


@app.get("/creations")
def creations():
    return {"items": creative.list_creations(CREATIONS)}


@app.get("/creations/{cid}")
def one_creation(cid: str):
    item = creative.get_creation(CREATIONS, cid)
    if not item:
        raise HTTPException(404, "not found")
    return item


@app.get("/media/{name}")
def media(name: str):
    path = (CREATIONS / name).resolve()
    if not str(path).startswith(str(CREATIONS.resolve())) or not path.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(path)


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
    log_event("job", f"queued {job_id}")
    return st


@app.post("/job/cancel")
def cancel(body: CancelIn):
    job_id = body.job_id or body.id or ""
    CANCEL.write_text(json.dumps({"job_id": job_id, "at": utc_ts()}))
    st = write_status(job_id=None, job_title=None, cache="idle", mode="idle", progress=None, message="Cancel requested")
    st.update({"status": "cancelled", "cancelled": True, "id": job_id, "job_id": job_id})
    log_event("job", f"cancel {job_id}")
    return st


@app.get("/app.js")
def app_js():
    return FileResponse(web_file("app.js"), media_type="text/javascript")


@app.get("/styles.css")
def app_css():
    return FileResponse(web_file("styles.css"), media_type="text/css")


@app.get("/icon.png")
def app_icon():
    return FileResponse(web_file("icon.png"), media_type="image/png")


if (WEB / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")
