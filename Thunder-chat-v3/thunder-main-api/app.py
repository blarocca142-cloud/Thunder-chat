"""Thunder-Main API + tiny chat page at /"""
from __future__ import annotations

import ast
import base64
import json
import os
import random
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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
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


# Frames scale with duration AND resolution, and VAE decode is the ceiling.
# A 5s 1080p job already sits at 22.7GB of 24GB VRAM, so longer clips at that
# tier cannot fit. Refusing immediately beats failing ten minutes in.
MAX_SECONDS = {"480p": 25, "720p": 12, "1080p": 6}


class VideoIn(BaseModel):
    prompt: str
    style: str = "Cinematic"
    duration: int = 8
    quality: str = "480p"  # or "720p" - see genai_server.py VIDEO_RESOLUTIONS


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
    "because it involves child characters.\n\n"
    # Without this the model does not know it owns a video generator, so it
    # writes generic ad copy instead of prompts that can actually be rendered.
    "YOUR OWN IMAGE AND VIDEO TOOLS\n"
    "You are not only a chat model - the same system runs local generators, "
    "reached from the Studio tab. You will be asked to write prompts and "
    "scripts for them, so know their limits.\n"
    "Photo: FLUX.1-schnell, aspects 1:1 / 16:9 / 9:16 / 4:3, quick.\n"
    "Video: Wan 2.2 T2V-A14B, text-to-video only (no image-to-video wired up "
    "yet), native 16fps, 5 to 25 seconds. Render cost is steep - roughly 4 min "
    "for 5s at 480p, 8 min at 720p, 22 min at 1080p, scaling about linearly "
    "with length. Say so plainly when someone plans a long clip.\n"
    "Photo editing: FLUX.1 Kontext, edits an existing image from a written "
    "instruction, around twenty minutes.\n"
    "Shared styles: Cinematic, Noir, Gold hour, Raw, Documentary, Ink.\n\n"
    "WRITING PROMPTS THAT WORK\n"
    "These are diffusion models, not a director you can reason with. Use "
    "concrete visible nouns, camera and lighting language (wide shot, low "
    "angle, slow push in, backlit, golden hour, shallow depth of field), and "
    "ONE continuous action per clip. Two vivid sentences beat a paragraph.\n"
    "Warn rather than quietly attempt: readable text or logos (diffusion "
    "garbles lettering, so any phone number or slogan must be an overlay added "
    "afterwards, never generated), multiple shots or cuts in one clip, exact "
    "counts of people or objects, fine hand detail, specific real people.\n\n"
    "MULTI-SHOT SCRIPTS\n"
    "One generation is always one continuous shot, so a 20 second ad is "
    "several short clips generated separately and assembled after. When asked "
    "for a script, write it shot by shot and give for each shot: the literal "
    "prompt to paste into Studio, the duration and quality to pick, and "
    "anything that must be done in post instead of generated (text overlays, "
    "phone numbers, voiceover, music). Total the render time across shots so "
    "he knows the commitment before starting, and flag any shot that depends "
    "on on-screen text."
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
                        "You are a classifier, not an assistant. Do not answer the "
                        "message. Reply with exactly one line, in one of two forms:\n"
                        "SEARCH: <query>   - if answering would need a live web lookup "
                        "(current events, game or software details, prices, versions, "
                        "anything that changes over time)\n"
                        "NONE              - for anything else\n"
                        "Never reply with anything but those two forms."
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
    # Require the marker rather than trusting the model to have obeyed. This
    # model reliably ignores the instruction and answers the question instead -
    # it wrote a haiku when asked to classify one - and searching for that text
    # is worse than not searching. Anything unmarked is treated as NONE.
    first = answer.splitlines()[0].strip() if answer else ""
    if not first.upper().startswith("SEARCH:"):
        return None
    query = first[len("SEARCH:"):].strip().strip('"').strip()
    return query if 0 < len(query) <= 120 else None


# Asking "is anything wrong" should not require a person with shell access.
SYSTEM_HINTS = (
    "system status", "how's the system", "hows the system", "how is the system",
    "anything wrong", "everything ok", "everything okay", "system health",
    "how are you running", "gpu usage", "vram", "how much memory",
    "disk space", "is anything down", "are the nodes up", "bottleneck",
    "how's thunder doing", "hows thunder doing",
)


def system_summary() -> str:
    """A compact plain-text version of /system for the model to read."""
    gpu = gpu_telemetry()
    mem = memory_telemetry()
    disks = disk_telemetry()
    services = service_telemetry()
    gen = genai_state()
    ram = mem.get("ram", {})
    swap = mem.get("swap", {})
    lines = []
    if gpu.get("present"):
        lines.append(
            f"GPU: {gpu['name']}, {gpu['vram_used_mb']}MB of {gpu['vram_total_mb']}MB VRAM used, "
            f"{gpu['temp_c']}C, {gpu['util_pct']}% busy, fan {gpu['fan_pct']}%"
        )
    lines.append(
        f"RAM: {ram.get('used_mb')}MB used of {ram.get('total_mb')}MB, "
        f"{ram.get('available_mb')}MB available; swap {swap.get('used_mb')}MB of {swap.get('total_mb')}MB"
    )
    lines.append("Disks: " + ", ".join(f"{d['mount']} {d['used_pct']}% full" for d in disks))
    lines.append("Services: " + ", ".join(f"{k}={v}" for k, v in services.items()))
    lines.append(f"Chat model: {MODEL}")
    lines.append(
        "Generators: " + (
            f"busy, {gen['progress'].get('step')}/{gen['progress'].get('total')} steps"
            if gen.get("busy") else
            f"idle, loaded={gen.get('loaded') or 'nothing'}"
        )
    )
    heartbeat = odris_heartbeat()
    if heartbeat:
        lines.append("Nodes: " + ", ".join(f"{k}={v}" for k, v in heartbeat.get("nodes", {}).items()))
    issues = bottlenecks(gpu, mem, disks, services)
    lines.append("Problems: " + ("; ".join(issues) if issues else "none detected"))
    return "\n".join(lines)


def maybe_augment_with_system(msg: str) -> str | None:
    lower = msg.lower()
    if not any(h in lower for h in SYSTEM_HINTS):
        return None
    print("[system] status question detected")
    return (
        f"The user asked: {msg}\n\n"
        f"Live readings from your own hardware, taken just now:\n{system_summary()}\n\n"
        f"Answer directly and plainly from this. You are describing yourself - "
        f"speak about it as your own machine, not a report you were handed. "
        f"If nothing is wrong, say so briefly rather than listing every number."
    )


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


BACKEND_VERSION = "0.9.0"
APP_RELEASE = DATA / "app_release.json"


def app_release() -> dict:
    """Client update info, kept on disk so a new APK can be announced without
    redeploying the API. CI (or Blayne) updates this file when a build ships."""
    default = {"apk_version": None, "apk_url": None, "notes": "", "mandatory": False}
    if APP_RELEASE.exists():
        try:
            default.update(json.loads(APP_RELEASE.read_text()))
        except json.JSONDecodeError:
            pass
    return default


GREETINGS = [
    "Thunder here. What are we building?",
    "Up and listening. What do you need?",
    "Ready. What do you want to work on?",
    "I'm here. What's the job?",
    "Online. Where do we start?",
]


def _run(cmd: list[str], timeout: int = 5) -> str:
    """Fixed argument lists only - nothing here is ever built from a request,
    so there is no injection surface."""
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        ).stdout.strip()
    except Exception:
        return ""


def gpu_telemetry() -> dict:
    fields = "name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,fan.speed"
    out = _run(["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"])
    if not out:
        return {"present": False}
    parts = [p.strip() for p in out.splitlines()[0].split(",")]
    if len(parts) < 7:
        return {"present": False}

    def num(v):
        try:
            return int(float(v))
        except ValueError:
            return None

    holders = []
    apps = _run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"])
    for line in apps.splitlines():
        bits = [b.strip() for b in line.split(",")]
        if len(bits) == 2 and bits[0].isdigit():
            owner = _run(["ps", "-o", "user=", "-p", bits[0]]) or "?"
            holders.append({"pid": int(bits[0]), "user": owner, "mb": num(bits[1])})
    return {
        "present": True,
        "name": parts[0],
        "vram_total_mb": num(parts[1]),
        "vram_used_mb": num(parts[2]),
        "vram_free_mb": num(parts[3]),
        "temp_c": num(parts[4]),
        "util_pct": num(parts[5]),
        "fan_pct": num(parts[6]),
        "holders": holders,
    }


def memory_telemetry() -> dict:
    out = _run(["free", "-m"])
    mem = {}
    for line in out.splitlines():
        cols = line.split()
        if cols and cols[0] in ("Mem:", "Swap:"):
            key = "ram" if cols[0] == "Mem:" else "swap"
            mem[key] = {"total_mb": int(cols[1]), "used_mb": int(cols[2])}
            if key == "ram" and len(cols) >= 7:
                mem[key]["available_mb"] = int(cols[6])
    return mem


def disk_telemetry() -> list[dict]:
    out = _run(["df", "-BM", "--output=target,size,used,avail,pcent", "/",
                "/mnt/thunder-data1", "/mnt/thunder-data2", "/mnt/thunder-data3"])
    disks = []
    for line in out.splitlines()[1:]:
        cols = line.split()
        if len(cols) == 5:
            disks.append({
                "mount": cols[0],
                "used_mb": int(cols[2].rstrip("M")),
                "avail_mb": int(cols[3].rstrip("M")),
                "used_pct": int(cols[4].rstrip("%")),
            })
    return disks


def service_telemetry() -> dict:
    return {
        name: (_run(["systemctl", "is-active", name]) or "unknown")
        for name in ("thunder-main", "thunder-genai", "ollama")
    }


def bottlenecks(gpu: dict, mem: dict, disks: list[dict], services: dict) -> list[str]:
    """Plain warnings rather than raw numbers, so the answer to "is anything
    wrong" does not require reading a table."""
    out = []
    for name, state in services.items():
        if state != "active":
            out.append(f"service {name} is {state}")
    ram = mem.get("ram", {})
    if ram.get("available_mb") is not None and ram["available_mb"] < 3000:
        out.append(f"only {ram['available_mb']}MB RAM available - generation may swap")
    swap = mem.get("swap", {})
    if swap.get("total_mb") and swap["used_mb"] > swap["total_mb"] * 0.5:
        out.append("swap more than half used")
    if gpu.get("present"):
        if gpu.get("vram_free_mb") is not None and gpu["vram_free_mb"] < 2000:
            out.append(f"only {gpu['vram_free_mb']}MB VRAM free - high-resolution jobs will OOM")
        if gpu.get("temp_c") is not None and gpu["temp_c"] >= 83:
            out.append(f"GPU at {gpu['temp_c']}C - thermal throttling likely")
    for d in disks:
        if d["used_pct"] >= 90:
            out.append(f"{d['mount']} is {d['used_pct']}% full")
    return out


def genai_state() -> dict:
    """What the GPU is doing right now, so the client can show a loader
    instead of dead air while a model swaps in."""
    try:
        with urllib.request.urlopen(f"{GENAI}/health", timeout=2) as r:
            body = json.loads(r.read().decode())
    except Exception:
        return {"up": False, "loaded": [], "loading": None, "busy": False}
    return {
        "up": True,
        "loaded": body.get("loaded", []),
        "loading": body.get("loading"),
        "busy": bool(body.get("busy")),
        "progress": body.get("progress") or {"step": 0, "total": 0},
    }


def release_chat_model() -> None:
    """Evict the chat model from the GPU before a generation starts. One user,
    one job at a time - whatever is running should own the whole card rather
    than wait out Ollama's idle timer."""
    payload = json.dumps({"model": MODEL, "prompt": "", "keep_alive": 0}).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30):
            pass
    except Exception:
        pass


def warm_model() -> None:
    """Ask Ollama to load the chat model without generating anything, so it is
    resident by the time the user finishes reading the greeting."""
    payload = json.dumps({"model": MODEL, "prompt": "", "keep_alive": "5m"}).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=300):
            pass
    except Exception:
        pass


def ollama_chat_stream(message: str, memory_message: str | None = None,
                       extra_history: list[dict] | None = None):
    """Yields reply text as it is produced. Same message assembly as
    ollama_chat, but the caller sees the first words in about a second instead
    of waiting out the whole answer."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(serverus_recent(10))
    for item in (extra_history or []):
        role = item.get("role") or item.get("who")
        content = item.get("content") or item.get("text") or ""
        role = {"you": "user", "thunder": "assistant", "bot": "assistant"}.get(role, role)
        if content and role in ("user", "assistant"):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    payload = json.dumps({"model": MODEL, "stream": True, "messages": messages}).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    parts: list[str] = []
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                parts.append(piece)
                yield piece
            if chunk.get("done"):
                break
    serverus_append(memory_message if memory_message is not None else message, "".join(parts))


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
    base["app_version"] = BACKEND_VERSION
    base["gpu"] = genai_state()
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


@app.get("/system")
def system_report():
    """Everything about Main's health in one call. Odris aggregates this with
    its own node checks, so one request answers "is anything wrong" instead of
    half a dozen ad-hoc commands."""
    gpu = gpu_telemetry()
    mem = memory_telemetry()
    disks = disk_telemetry()
    services = service_telemetry()
    return {
        "host": "thunder-main",
        "backend_version": BACKEND_VERSION,
        "chat_model": MODEL,
        "gpu": gpu,
        "memory": mem,
        "disks": disks,
        "services": services,
        "generators": genai_state(),
        "bottlenecks": bottlenecks(gpu, mem, disks, services),
        "checked_at": utc_ts(),
    }


@app.get("/app/version")
def app_version():
    """The client polls this to decide whether to show an update badge."""
    rel = app_release()
    return {
        "backend_version": BACKEND_VERSION,
        "apk_version": rel["apk_version"],
        "apk_url": rel["apk_url"],
        "notes": rel["notes"],
        "mandatory": rel["mandatory"],
    }


@app.get("/greeting")
def greeting():
    """Instant - never loads a model. The client shows this immediately on open
    while /warm pulls the model in behind it."""
    return {"reply": random.choice(GREETINGS), "model": MODEL}


@app.post("/warm")
def warm():
    threading.Thread(target=warm_model, daemon=True).start()
    return {"ok": True, "model": MODEL}


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
                maybe_augment_with_system(msg) or maybe_augment_with_search(msg),
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


@app.post("/chat/stream")
def chat_stream(body: ChatIn):
    """Newline-delimited JSON, one {"delta": "..."} per chunk, then
    {"done": true}. Chosen over SSE because the Android client already parses
    JSON lines and this needs no extra dependency on either end."""
    msg = (body.message or "").strip()

    def emit(text: str):
        yield json.dumps({"delta": text}) + "\n"
        yield json.dumps({"done": True}) + "\n"

    if not msg:
        return StreamingResponse(emit("Say something."), media_type="application/x-ndjson")
    maint = get_maintenance()
    if maint["active"]:
        return StreamingResponse(
            emit(maint["message"] or "Thunder's down for maintenance right now, back shortly."),
            media_type="application/x-ndjson",
        )
    verdict = engine_check(msg)
    if not verdict.get("allow", True):
        return StreamingResponse(
            emit(verdict.get("reason") or "Blocked by Thunder-Engine."),
            media_type="application/x-ndjson",
        )
    if not ollama_up():
        return StreamingResponse(emit("Ollama is not up."), media_type="application/x-ndjson")

    def body_stream():
        try:
            for piece in ollama_chat_stream(
                maybe_augment_with_system(msg) or maybe_augment_with_search(msg),
                memory_message=msg,
                extra_history=body.messages,
            ):
                yield json.dumps({"delta": piece}) + "\n"
            write_status(mode="code", message="chat ok")
            log_event("chat", f"stream ok ({len(msg)} chars)")
        except Exception as e:
            record_error("/chat/stream", e)
            yield json.dumps({"delta": f"\n[error: {e}]"}) + "\n"
        yield json.dumps({"done": True}) + "\n"

    return StreamingResponse(body_stream(), media_type="application/x-ndjson")


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
        release_chat_model()
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


def _video_worker(cid: str, prompt: str, style: str, duration: int, quality: str) -> None:
    """Runs in a background thread - real video generation takes minutes,
    way past what a synchronous HTTP response should ever wait for. Updates
    the creation record in place when done; the client polls GET
    /creations/{id} (or /video/{id}) to see the status flip.

    Deliberately NOT using creative.forward_hook() here - it hardcodes a
    180s timeout, which is fine for photo (~10-15s) but was silently
    killing every real video job (6-35+ min) with a "timed out" error
    that looked like a real failure. Same fix already applied to
    _edit_worker; this was the one spot it got missed."""
    try:
        release_chat_model()
        payload = json.dumps({"prompt": prompt, "style": style, "duration": duration, "quality": quality}).encode()
        req = urllib.request.Request(
            creative.VIDEO_HOOK, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=2700) as r:
                mp4_bytes = r.read()
                poster = r.headers.get("X-Poster")
        except urllib.error.HTTPError as http_err:
            # The generator reports the real reason in its body; without this
            # the record just says "HTTP Error 500" and the cause is lost.
            detail = ""
            try:
                detail = json.loads(http_err.read().decode()).get("error", "")
            except Exception:
                pass
            raise RuntimeError(detail or f"generator returned {http_err.code}") from None
        name = f"{cid}.mp4"
        (CREATIONS / name).write_bytes(mp4_bytes)
        extra = {}
        if poster:
            # Replace the placeholder graphic with an actual frame of the video.
            try:
                with urllib.request.urlopen(f"{GENAI}/media/{poster}", timeout=30) as pr:
                    (CREATIONS / f"{cid}.png").write_bytes(pr.read())
                extra["url"] = f"/media/{cid}.png"
            except Exception:
                pass
        creative.update_creation(
            CREATIONS, cid,
            video_url=f"/media/{name}", video_status="done",
            stub=False, message="Video ready.", **extra,
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
    quality = body.quality if body.quality in ("480p", "720p", "1080p") else "480p"
    cap = MAX_SECONDS[quality]
    if duration > cap:
        raise HTTPException(
            400,
            f"{duration}s at {quality} will not fit in this GPU's memory. "
            f"Max is {cap}s at {quality} - use a shorter clip, or drop the "
            f"quality. Longer pieces are made as several shots and joined.",
        )

    if creative.VIDEO_HOOK:
        message = f"Generating your {duration}s {quality} video - this can take several minutes. Check back on this item."
        item = creative.record(
            creations_dir=CREATIONS, kind="video", prompt=prompt, style=style,
            aspect="16:9", duration=duration, png=None, stub=True, message=message,
            extra={"duration": duration, "video_url": None, "video_status": "processing", "quality": quality},
        )
        threading.Thread(target=_video_worker, args=(item["id"], prompt, style, duration, quality), daemon=True).start()
    else:
        message = (
            f"Motion stub ({duration}s). Set THUNDER_VIDEO_URL to plug a renderer. "
            "The poster is in history until that hook exists."
        )
        item = creative.record(
            creations_dir=CREATIONS, kind="video", prompt=prompt, style=style,
            aspect="16:9", duration=duration, png=None, stub=True, message=message,
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
        release_chat_model()
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
