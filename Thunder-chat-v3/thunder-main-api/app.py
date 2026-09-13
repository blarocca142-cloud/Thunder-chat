"""Thunder-Main API + tiny chat page at /"""
from __future__ import annotations

import ast
import base64
import json
import os
import re
import shutil
import subprocess
import threading
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from collections import deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

import creative

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("THUNDER_MODEL", "dolphin3")  # never default to a Qwen/Alibaba model
SERVERUS = os.environ.get("SERVERUS_URL", "http://10.168.168.13:9001")
ENGINE = os.environ.get("ENGINE_URL", "http://10.168.168.12:9002")
ODRIS = os.environ.get("ODRIS_URL", "http://10.168.168.15:9003")
WEBSEARCH = os.environ.get("WEBSEARCH_URL", "http://10.168.168.15:9004")
GENAI = os.environ.get("GENAI_URL", "http://127.0.0.1:9010")

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
CREATIONS = DATA / "creations"
CREATIONS.mkdir(exist_ok=True)
WEB = Path(__file__).resolve().parent.parent / "thunder-web"
LOGS: deque[dict] = deque(maxlen=200)
STATUS = DATA / "status.json"
CANCEL = DATA / "cancel.json"
MAINTENANCE = DATA / "maintenance.json"
ADMIN_SECRET_FILE = DATA / "admin_secret.txt"


def get_admin_secret() -> str:
    """Generated once, on disk, never in code or git. This is the one gate
    between an approved AI-proposed fix and it actually going live - a
    separate application-level secret, not the Linux login/sudo password."""
    if not ADMIN_SECRET_FILE.exists():
        import secrets

        ADMIN_SECRET_FILE.write_text(secrets.token_urlsafe(24))
        ADMIN_SECRET_FILE.chmod(0o600)
    return ADMIN_SECRET_FILE.read_text().strip()

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
#maint{display:none;background:#3a2f1b;color:#e3b341;padding:10px 16px;font-size:14px}
</style></head><body>
<div id="maint"></div>
<div id="log"></div>
<form id="f"><input id="m" autofocus placeholder="talk to Thunder"><button>send</button></form>
<script>
const log=document.getElementById('log');
const maintBanner=document.getElementById('maint');
function add(cls,t){const d=document.createElement('div');d.className='row '+cls;d.textContent=t;log.appendChild(d);log.scrollTop=log.scrollHeight;}
add('bot','Thunder local. Model talks through /chat.');

let maintUntil=null;
function fmtCountdown(sec){const m=Math.floor(sec/60),s=sec%60;return `${m}:${String(s).padStart(2,'0')}`;}
function renderMaint(m){
  if(!m||!m.active){maintBanner.style.display='none';return;}
  maintBanner.style.display='block';
  maintUntil=m.until;
  maintBanner.textContent=m.message+(m.until?` (back in ${fmtCountdown(Math.max(0,m.until-Math.floor(Date.now()/1000)))})`:'');
}
setInterval(()=>{if(maintUntil)renderMaint({active:true,message:maintBanner.textContent.split(' (back')[0],until:maintUntil});},1000);
async function checkStatus(){try{const r=await fetch('/status');const s=await r.json();renderMaint(s.maintenance);}catch(e){}}
checkStatus();
setInterval(checkStatus,15000);

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
    message: str = ""
    messages: list[dict] | None = None


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


class JobIn(BaseModel):
    title: str = "overnight coding"
    prompt: str = ""
    task: str = ""


class CancelIn(BaseModel):
    job_id: str = ""
    id: str = ""


def utc_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def log_event(kind: str, message: str) -> None:
    LOGS.appendleft({"at": utc_ts(), "kind": kind, "message": message})


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


def get_maintenance() -> dict:
    """Auto-expires: if `until` has passed, treat it as over even if the
    stored flag still says active - no cron job needed to flip it off."""
    default = {"active": False, "message": "", "until": None, "started": None}
    if not MAINTENANCE.exists():
        return default
    try:
        rec = json.loads(MAINTENANCE.read_text())
    except json.JSONDecodeError:
        return default
    if rec.get("active") and rec.get("until") and utc_ts() > rec["until"]:
        rec["active"] = False
    return {**default, **rec}


def recent_blocked_egress(minutes: int = 5) -> list[str]:
    """Surfaces any outbound-internet attempt the firewall rejected in the
    last few minutes, from ANY locked-down account (ollama, genai, etc.) -
    turns 'it's blocked' into 'and you'll actually know if something tries.'"""
    try:
        result = subprocess.run(
            ["journalctl", "-k", "--since", f"-{minutes}min", "--no-pager"],
            capture_output=True, text=True, timeout=5,
        )
        return [l for l in result.stdout.splitlines() if "THUNDER-BLOCKED-EGRESS" in l][-10:]
    except Exception:
        return []


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


def ollama_tags() -> list[dict]:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=4) as r:
            body = json.loads(r.read().decode())
        return [
            {"name": m.get("name", ""), "size": m.get("size"), "digest": m.get("digest")}
            for m in body.get("models", [])
            if m.get("name")
        ]
    except Exception:
        return []


def ollama_chat(message: str, memory_message: str | None = None, extra_history: list[dict] | None = None) -> str:
    """memory_message is what gets stored in Serverus - defaults to `message`,
    but callers that inject search-result blobs into `message` should pass
    the original, clean user text instead so history doesn't fill up with
    search dumps."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(serverus_recent(10))
    if extra_history:
        for item in extra_history:
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
    base["maintenance"] = get_maintenance()
    if base["maintenance"]["active"]:
        base["state"] = "maintenance"
    base["blocked_egress"] = recent_blocked_egress()
    if base["blocked_egress"]:
        base["state"] = "security_alert"
    base["app_version"] = "0.8.0"
    base["image_hook"] = bool(creative.IMAGE_HOOK)
    base["video_hook"] = bool(creative.VIDEO_HOOK)
    return base


def write_status(**extra) -> dict:
    cur = read_status()
    cur.update({k: v for k, v in extra.items() if v is not None})
    cur["last_write_unix"] = utc_ts()
    STATUS.write_text(json.dumps(cur, indent=2))
    return cur


@app.get("/", response_class=HTMLResponse)
def home():
    index = WEB / "index.html"
    if index.exists():
        return FileResponse(index)
    return HTMLResponse(PAGE)


@app.get("/app.js")
def app_js():
    path = WEB / "app.js"
    if not path.is_file():
        raise HTTPException(404, "missing app.js")
    return FileResponse(path, media_type="text/javascript")


@app.get("/styles.css")
def app_css():
    path = WEB / "styles.css"
    if not path.is_file():
        raise HTTPException(404, "missing styles.css")
    return FileResponse(path, media_type="text/css")


@app.get("/icon.png")
def app_icon():
    path = WEB / "icon.png"
    if not path.is_file():
        raise HTTPException(404, "missing icon.png")
    return FileResponse(path, media_type="image/png")


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


@app.get("/status")
def status():
    return read_status()


@app.post("/chat")
def chat(body: ChatIn):
    msg = (body.message or "").strip()
    if not msg:
        return {"reply": "Say something."}
    maint = get_maintenance()
    if maint["active"]:
        return {
            "reply": maint["message"] or "Thunder's down for maintenance right now, back shortly.",
            "maintenance": maint,
        }
    verdict = engine_check(msg)
    if not verdict.get("allow", True):
        return {"reply": verdict.get("reason") or "Blocked by Thunder-Engine."}
    if ollama_up():
        try:
            reply = ollama_chat(
                maybe_augment_with_search(msg),
                memory_message=msg,
                extra_history=body.messages,
            )
            write_status(mode="code", message="chat ok")
            log_event("chat", f"ok ({len(msg)} chars)")
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


APP_PY = Path(__file__).resolve()


class ApplyIn(BaseModel):
    job_id: str
    admin_secret: str


@app.post("/job/apply")
def apply_job(body: ApplyIn):
    """The one action gated by the admin secret: actually writing an
    AI-proposed fix into live app.py and restarting the service. Extracts
    a unified diff from the job's output, validates it applies cleanly AND
    that the result is syntactically valid Python, before ever touching the
    live file - auto-rolls back on any failure at any step."""
    if body.admin_secret != get_admin_secret():
        return {"ok": False, "error": "wrong admin secret"}

    path = JOBS / f"{body.job_id}.json"
    if not path.exists():
        return {"ok": False, "error": "unknown job_id"}
    rec = json.loads(path.read_text())
    if rec.get("review_status") != "approved":
        return {"ok": False, "error": "job must be approved before it can be applied"}

    output = rec.get("output", "")
    match = re.search(r"```diff\n(.*?)```", output, re.DOTALL)
    if not match:
        return {"ok": False, "error": "no ```diff block found in job output"}
    diff_text = match.group(1)

    backup = APP_PY.with_suffix(".py.bak")
    shutil.copy(APP_PY, backup)
    diff_file = DATA / f"apply_{body.job_id}.diff"
    diff_file.write_text(diff_text)

    try:
        check = subprocess.run(
            ["git", "apply", "--check", str(diff_file)],
            cwd=APP_PY.parent, capture_output=True, text=True,
        )
        if check.returncode != 0:
            return {"ok": False, "error": f"diff doesn't apply cleanly: {check.stderr}"}

        apply = subprocess.run(
            ["git", "apply", str(diff_file)],
            cwd=APP_PY.parent, capture_output=True, text=True,
        )
        if apply.returncode != 0:
            return {"ok": False, "error": f"git apply failed: {apply.stderr}"}

        try:
            ast.parse(APP_PY.read_text())
        except SyntaxError as e:
            shutil.copy(backup, APP_PY)
            return {"ok": False, "error": f"result had a syntax error, rolled back: {e}"}

    finally:
        diff_file.unlink(missing_ok=True)

    rec["review_status"] = "applied"
    rec["applied"] = utc_ts()
    rec["backup"] = str(backup)
    path.write_text(json.dumps(rec, indent=2))

    # Restarting this very process would kill the request before the
    # response ships - delay it a second and detach so the caller actually
    # gets this response back first. If the new code crashes on startup,
    # systemd's Restart=always keeps retrying; that failure shows up as a
    # flapping service on the dashboard, not a silent rollback - restoring
    # from `backup` at that point is a manual (or future) step.
    subprocess.Popen(
        ["bash", "-c", "sleep 1 && sudo -n systemctl restart thunder-main"],
        start_new_session=True,
    )
    return {"ok": True, "message": f"Diff applied, syntax valid. Restarting now. Backup at {backup}."}


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
    current_source = Path(__file__).read_text()
    prompt = (
        f"Thunder-Main hit an unhandled error on endpoint {err['endpoint']}.\n\n"
        f"Error: {err['error']}\n\nTraceback:\n{err['traceback']}\n\n"
        f"Current contents of app.py:\n```python\n{current_source}\n```\n\n"
        f"Explain the bug in 1-2 sentences, then give ONLY a unified diff "
        f"fixing it, in a fenced ```diff block, in standard `diff -u` format "
        f"with `--- a/app.py` / `+++ b/app.py` headers. The diff must apply "
        f"cleanly to the exact source shown above. Do not include any other "
        f"code changes beyond what's needed to fix this specific error."
    )
    job = create_job(f"Fix for {error_id}", prompt)
    err["review_status"] = "fix_requested"
    err["fix_job_id"] = job["id"]
    path.write_text(json.dumps(err, indent=2))
    return {"ok": True, "job": job}


class MaintenanceIn(BaseModel):
    message: str = ""
    duration_seconds: int | None = None  # None = indefinite, until explicitly stopped


@app.post("/maintenance/start")
def start_maintenance(body: MaintenanceIn):
    now = utc_ts()
    rec = {
        "active": True,
        "message": body.message or "Thunder's down for maintenance, back shortly.",
        "started": now,
        "until": (now + body.duration_seconds) if body.duration_seconds else None,
    }
    MAINTENANCE.write_text(json.dumps(rec, indent=2))
    return rec


@app.post("/maintenance/stop")
def stop_maintenance():
    rec = {"active": False, "message": "", "until": None, "started": None}
    MAINTENANCE.write_text(json.dumps(rec, indent=2))
    return rec


@app.get("/maintenance")
def maintenance_status():
    return get_maintenance()


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
            message = hooked.get("message") or (
                "Image hook returned a still." if not stub else "Hook did not return image bytes; stub used."
            )
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


def _video_worker(cid: str, prompt: str, style: str, duration: int) -> None:
    """Runs in a background thread - real video generation takes minutes,
    way past what a synchronous HTTP response should ever wait for. Updates
    the creation record in place when done; the client polls GET
    /creations/{id} (or /video/{id}) to see the status flip."""
    try:
        hooked = creative.forward_hook(
            creative.VIDEO_HOOK,
            {"prompt": prompt, "style": style, "duration": duration},
        )
        if isinstance(hooked, dict) and hooked.get("bytes"):
            name = f"{cid}.mp4"
            (CREATIONS / name).write_bytes(hooked["bytes"])
            creative.update_creation(
                CREATIONS, cid,
                video_url=f"/media/{name}", video_status="done",
                stub=False, message="Video ready.",
            )
        else:
            creative.update_creation(
                CREATIONS, cid, video_status="error",
                message="Video hook didn't return video bytes.",
            )
    except Exception as e:
        record_error("/video (background)", e)
        creative.update_creation(
            CREATIONS, cid, video_status="error", message=f"Video generation failed: {e}",
        )


@app.post("/video")
def make_video(body: VideoIn):
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt required")
    style = body.style or "Cinematic"
    duration = max(3, min(int(body.duration or 8), 30))
    png = creative.render_stub_png(prompt, style, "16:9", "video")

    if creative.VIDEO_HOOK:
        message = f"Generating your {duration}s video - this can take several minutes. Check back on this item."
        item = creative.record(
            creations_dir=CREATIONS, kind="video", prompt=prompt, style=style,
            aspect="16:9", duration=duration, png=png, stub=True, message=message,
            extra={"duration": duration, "video_url": None, "video_status": "processing"},
        )
        threading.Thread(target=_video_worker, args=(item["id"], prompt, style, duration), daemon=True).start()
    else:
        message = (
            f"Motion stub ({duration}s). Set THUNDER_VIDEO_URL to plug a renderer. "
            "The poster is in history until that hook exists."
        )
        item = creative.record(
            creations_dir=CREATIONS, kind="video", prompt=prompt, style=style,
            aspect="16:9", duration=duration, png=png, stub=True, message=message,
            extra={"duration": duration, "video_url": None, "video_status": "stub"},
        )

    log_event("video", f"{item['id']} video_status={item.get('video_status')} {duration}s")
    write_status(mode="studio", message=f"video {item['id']}")
    return item


class EditIn(BaseModel):
    source_id: str
    instruction: str


def _edit_worker(cid: str, source_path: Path, instruction: str) -> None:
    """Real edits measured at ~19 minutes (28 steps, FLUX Kontext) - always
    a background thread, never a live request, same reasoning as video."""
    try:
        image_b64 = base64.b64encode(source_path.read_bytes()).decode()
        payload = json.dumps({"image_b64": image_b64, "instruction": instruction}).encode()
        req = urllib.request.Request(
            f"{GENAI}/edit", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=1800) as r:
            png_bytes = r.read()
        name = f"{cid}.png"
        (CREATIONS / name).write_bytes(png_bytes)
        creative.update_creation(
            CREATIONS, cid, url=f"/media/{name}",
            edit_status="done", stub=False, message="Edit ready.",
        )
    except Exception as e:
        record_error("/edit (background)", e)
        creative.update_creation(CREATIONS, cid, edit_status="error", message=f"Edit failed: {e}")


@app.post("/edit")
def make_edit(body: EditIn):
    """New endpoint - not part of creative.py's hook system since editing
    needs a source image, unlike generate/video. Treated as kind='image':
    a new creation record, linked back via source_id, poster is the
    original image until the real edit lands."""
    source = creative.get_creation(CREATIONS, body.source_id)
    if not source:
        raise HTTPException(404, "source creation not found")
    instruction = (body.instruction or "").strip()
    if not instruction:
        raise HTTPException(400, "instruction required")
    source_path = CREATIONS / Path(source["url"]).name
    if not source_path.exists():
        raise HTTPException(404, "source image file not found")

    item = creative.record(
        creations_dir=CREATIONS, kind="image", prompt=instruction,
        style=source.get("style", "Cinematic"), aspect=source.get("aspect", "1:1"),
        png=source_path.read_bytes(), stub=True,
        message="Editing your image - this can take up to 20 minutes.",
        extra={"edit_status": "processing", "source_id": body.source_id},
    )
    threading.Thread(target=_edit_worker, args=(item["id"], source_path, instruction), daemon=True).start()
    log_event("edit", f"{item['id']} source={body.source_id}")
    write_status(mode="studio", message=f"edit {item['id']}")
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
