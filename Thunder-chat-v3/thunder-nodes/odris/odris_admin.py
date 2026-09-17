"""Odris Admin: dashboard + a distinct ops-assistant persona for Blayne,
separate from Thunder (the user-facing chat AI on Main). Both ultimately
run on Main's GPU - it's the only one in the fleet - but Odris has its
own system prompt and its own context (live system data, not user chat
history), so it's a genuinely separate assistant, not Thunder wearing a
different hat. Stdlib only, no deps.
"""
import base64
import json
import re
import secrets
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 9005
MAIN = "http://10.168.168.10:8080"
OLLAMA = "http://10.168.168.10:11434"
SERVERUS = "http://10.168.168.13:9001"

# Whole-dashboard auth - nobody on the LAN gets in without this, not just
# the apply-fix action. Generated once, on disk, never in code or git.
DASHBOARD_PASSWORD_FILE = Path.home() / "dashboard_password.txt"


def get_dashboard_password() -> str:
    if not DASHBOARD_PASSWORD_FILE.exists():
        DASHBOARD_PASSWORD_FILE.write_text(secrets.token_urlsafe(16))
        DASHBOARD_PASSWORD_FILE.chmod(0o600)
    return DASHBOARD_PASSWORD_FILE.read_text().strip()


# Set once per process. Browsers reliably return cookies on fetch(); several
# mobile browsers do NOT re-send HTTP Basic credentials on same-origin fetch,
# which is why the dashboard logged in fine and then every panel stayed empty -
# each API call came back 401, the page parsed the error as data, and the render
# died. Basic gets you in, the cookie keeps you in.
SESSION_TOKEN = secrets.token_urlsafe(24)


def _cookie_ok(handler) -> bool:
    raw = handler.headers.get("Cookie", "")
    for part in raw.split(";"):
        name, _, value = part.strip().partition("=")
        if name == "odris_session" and value and secrets.compare_digest(
                value, SESSION_TOKEN):
            return True
    return False


def check_auth(handler) -> bool:
    if _cookie_ok(handler):
        return True
    header = handler.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:]).decode()
        _, _, password = decoded.partition(":")
    except Exception:
        return False
    if not secrets.compare_digest(password, get_dashboard_password()):
        return False
    handler.grant_session = True
    return True

ODRIS_SYSTEM_PROMPT = (
    "You are Odris, Blayne's ops/admin assistant for the Thunder AI stack. "
    "You are NOT Thunder (the user-facing chat AI) - you're the separate "
    "assistant that helps Blayne monitor and manage the system: node health, "
    "job history, errors, and what needs review. Be direct and concise, "
    "like a sharp sysadmin buddy, not a corporate status-report generator. "
    "You'll be given a live snapshot of system state before each question - "
    "use it to answer accurately rather than guessing."
)

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Odris Admin</title>
<style>
:root{color-scheme:dark light}
body{margin:0;background:#0b0d10;color:#e8edf2;font:15px/1.4 system-ui,sans-serif}
header{padding:14px 20px;border-bottom:1px solid #222;display:flex;justify-content:space-between;align-items:center}
header h1{font-size:16px;margin:0;color:#8ec8ff}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px;max-width:1200px;margin:0 auto}
@media (max-width:800px){.grid{grid-template-columns:1fr}}
.card{background:#12151a;border:1px solid #222;border-radius:10px;padding:14px}
.card h2{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:#8a94a3;margin:0 0 10px}
.node{display:flex;justify-content:space-between;padding:4px 0;font-size:14px}
.up{color:#7ee787}.down{color:#ff7b72}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{text-align:left;padding:4px 6px;border-bottom:1px solid #1c2027}
.pill{padding:2px 8px;border-radius:99px;font-size:11px}
.pill.done{background:#1b3a24;color:#7ee787}
.pill.error{background:#3a1b1b;color:#ff7b72}
.pill.running,.pill.queued{background:#3a2f1b;color:#e3b341}
.pill.pending{background:#222;color:#8a94a3}
.pill.approved{background:#1b3a24;color:#7ee787}
.pill.rejected{background:#3a1b1b;color:#ff7b72}
button{padding:5px 10px;border:0;border-radius:6px;background:#3b82f6;color:#fff;font-size:12px;cursor:pointer;margin-right:4px}
button.reject{background:#5b2b2b}
#chatlog{height:260px;overflow:auto;font-size:14px;margin-bottom:10px}
.row{margin:6px 0;white-space:pre-wrap}
.me{color:#8ec8ff}.bot{color:#c8f0c0}
form{display:flex;gap:8px}
input{flex:1;padding:8px;border-radius:8px;border:1px solid #333;background:#0b0d10;color:#fff}
.full{grid-column:1/-1}
small{color:#6b7280}
</style></head><body>
<header><h1>Odris - Thunder Ops</h1><small id="ts"></small></header>
<div class="grid">
  <div class="card full" id="securityCard" style="display:none;border-color:#ff7b72;background:#2a1414">
    <h2 style="color:#ff7b72">⚠ Security Alert - Blocked Outbound Attempts</h2>
    <div id="securityLog" style="font-size:12px;font-family:monospace;white-space:pre-wrap;max-height:150px;overflow:auto"></div>
  </div>
  <div class="card full">
    <h2>Talk to Odris</h2>
    <div id="chatlog"></div>
    <form id="f"><input id="m" placeholder="ask odris about system status, jobs, errors..."><button>send</button></form>
  </div>
  <div class="card"><h2>Node Health</h2><div id="nodes"></div></div>
  <div class="card"><h2>Thunder-Main Status</h2><div id="mainstatus"></div></div>
  <div class="card full" id="maintCard">
    <h2>Maintenance Mode</h2>
    <div id="maintState" style="margin-bottom:8px"></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
      <input id="maintMsg" placeholder="message shown to users" style="flex:2;min-width:160px;padding:6px;border-radius:6px;border:1px solid #333;background:#0b0d10;color:#fff">
      <input id="maintMin" type="number" placeholder="minutes (blank = indefinite)" style="flex:1;min-width:140px;padding:6px;border-radius:6px;border:1px solid #333;background:#0b0d10;color:#fff">
      <button onclick="startMaint()">start maintenance</button>
      <button class="reject" onclick="stopMaint()">stop maintenance</button>
    </div>
  </div>
  <div class="card full"><h2>Jobs Awaiting Review</h2><table id="jobs"></table></div>
  <div class="card full"><h2>Recent Errors</h2><table id="errors"></table></div>
  <div class="card full"><h2>Recent Conversation (Serverus)</h2><div id="serverus" style="font-size:13px;max-height:200px;overflow:auto"></div></div>
</div>
<script>
function showProblem(msg){
  const el = document.getElementById('ts');
  if (el) el.textContent = msg;
}
async function refresh(){
  let d;
  try {
    const r = await fetch('/api/overview', {credentials:'same-origin'});
    if (!r.ok) { showProblem('cannot load: HTTP ' + r.status + ' - reload the page'); return; }
    d = await r.json();
  } catch (e) {
    showProblem('cannot reach Odris: ' + e.message);
    return;
  }
  // One missing field must not blank every panel below it, which is exactly
  // what happened before: an error object came back where data was expected
  // and the whole render threw on the first field it touched.
  try {
  document.getElementById('ts').textContent = new Date().toLocaleTimeString();

  const blocked = (d.status && d.status.blocked_egress) || [];
  const secCard = document.getElementById('securityCard');
  if (blocked.length) {
    secCard.style.display = 'block';
    document.getElementById('securityLog').textContent = blocked.join('\n');
  } else {
    secCard.style.display = 'none';
  }

  const nodesEl = document.getElementById('nodes');
  nodesEl.innerHTML = '';
  const nodes = (d.heartbeat && d.heartbeat.nodes) || {};
  for (const [name, state] of Object.entries(nodes)) {
    nodesEl.innerHTML += `<div class="node"><span>${name}</span><span class="${state}">${state}</span></div>`;
  }

  const st = d.status || {};
  document.getElementById('mainstatus').innerHTML = `
    <div class="node"><span>model</span><span>${st.model||'?'}</span></div>
    <div class="node"><span>ollama</span><span class="${st.ollama?'up':'down'}">${st.ollama?'up':'down'}</span></div>
    <div class="node"><span>mode</span><span>${st.mode||'?'}</span></div>
    <div class="node"><span>cache</span><span>${st.cache||'?'}</span></div>
    <div class="node"><span>message</span><span>${st.message||''}</span></div>`;

  const m = st.maintenance || {active:false};
  const maintEl = document.getElementById('maintState');
  if (m.active) {
    const rem = m.until ? Math.max(0, m.until - Math.floor(Date.now()/1000)) : null;
    maintEl.innerHTML = `<span class="pill error">ACTIVE</span> ${m.message||''} ${rem!==null ? `(back in ${Math.floor(rem/60)}:${String(rem%60).padStart(2,'0')})` : '(indefinite)'}`;
  } else {
    maintEl.innerHTML = `<span class="pill done">off</span> users are getting normal chat`;
  }

  const jobsEl = document.getElementById('jobs');
  jobsEl.innerHTML = '<tr><th>title</th><th>status</th><th>review</th><th></th></tr>';
  (d.jobs || []).forEach(j => {
    const needsReview = (j.status==='done'||j.status==='error') && j.review_status==='pending';
    const canApply = j.review_status==='approved';
    let actions = '';
    if (needsReview) actions = `<button onclick="review('${j.id}','approved')">approve</button><button class="reject" onclick="review('${j.id}','rejected')">reject</button>`;
    else if (canApply) actions = `<button onclick="applyFix('${j.id}')">apply to live code</button>`;
    jobsEl.innerHTML += `<tr><td>${j.title}</td><td><span class="pill ${j.status}">${j.status}</span></td>
      <td><span class="pill ${j.review_status||'pending'}">${j.review_status||'pending'}</span></td>
      <td>${actions}</td></tr>`;
  });

  const errEl = document.getElementById('errors');
  errEl.innerHTML = '<tr><th>endpoint</th><th>error</th><th></th></tr>';
  (d.errors || []).forEach(e => {
    errEl.innerHTML += `<tr><td>${e.endpoint}</td><td>${(e.error||'').slice(0,80)}</td>
      <td>${e.review_status==='pending' ? `<button onclick="requestFix('${e.id}')">ask cache to fix</button>` : `<span class="pill">${e.review_status}</span>`}</td></tr>`;
  });

  const sEl = document.getElementById('serverus');
  sEl.innerHTML = (d.serverus || []).map(t => `<div class="row ${t.role==='user'?'me':'bot'}">${t.role}: ${t.content}</div>`).join('');

  } catch (e) {
    showProblem('render failed: ' + e.message);
  }
}

async function startMaint(){
  const message = document.getElementById('maintMsg').value.trim() || "Thunder's down for maintenance, back shortly.";
  const min = document.getElementById('maintMin').value.trim();
  const duration_seconds = min ? Math.round(parseFloat(min) * 60) : null;
  await fetch('/api/maintenance/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message, duration_seconds})});
  refresh();
}
async function stopMaint(){
  await fetch('/api/maintenance/stop', {method:'POST'});
  refresh();
}

async function review(job_id, decision){
  await fetch('/api/job/review', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({job_id, decision})});
  refresh();
}
async function applyFix(job_id){
  const admin_secret = prompt("Admin secret to deploy this to live code (one-time setup: cat thunder-data/admin_secret.txt on Main):");
  if (!admin_secret) return;
  const r = await fetch('/api/job/apply', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({job_id, admin_secret})});
  const j = await r.json();
  alert(j.ok ? j.message : ('Failed: ' + j.error));
  refresh();
}
async function requestFix(error_id){
  await fetch(`/api/errors/${error_id}/fix`, {method:'POST'});
  refresh();
}

const log = document.getElementById('chatlog');
function add(cls, t){ const d=document.createElement('div'); d.className='row '+cls; d.textContent=t; log.appendChild(d); log.scrollTop = log.scrollHeight; }
add('bot', "Odris here. Ask me about node health, jobs, or errors.");
document.getElementById('f').onsubmit = async (e) => {
  e.preventDefault();
  const v = document.getElementById('m').value.trim();
  if (!v) return;
  document.getElementById('m').value = '';
  add('me', v);
  add('bot', '...');
  try {
    const r = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message: v})});
    const j = await r.json();
    log.lastChild.textContent = j.reply || JSON.stringify(j);
  } catch (err) { log.lastChild.textContent = 'error: ' + err; }
};

refresh();
setInterval(refresh, 8000);
</script>
</body></html>"""


def get_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def post_json(url, payload, timeout=8):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def build_overview() -> dict:
    overview = {"status": {}, "heartbeat": {}, "jobs": [], "errors": [], "serverus": []}
    try:
        overview["status"] = get_json(f"{MAIN}/status")
    except Exception as e:
        overview["status"] = {"error": str(e)}
    try:
        overview["heartbeat"] = get_json("http://10.168.168.15:9003/heartbeat")
    except Exception:
        pass
    try:
        overview["jobs"] = get_json(f"{MAIN}/jobs?limit=15").get("jobs", [])
    except Exception:
        pass
    try:
        overview["errors"] = get_json(f"{MAIN}/errors?limit=15").get("errors", [])
    except Exception:
        pass
    try:
        overview["serverus"] = get_json(f"{SERVERUS}/recent?limit=10").get("turns", [])
    except Exception:
        pass
    return overview


JOB_ID_RE = re.compile(r"(job_\d{8}_\d{6}(?:_\d+)?)")


def latest_job_id():
    jobs = get_json(f"{MAIN}/jobs?limit=1").get("jobs", [])
    return jobs[0]["id"] if jobs else None


def parse_and_execute_command(msg: str) -> str | None:
    """Deterministic command handling, checked before the message ever
    reaches the LLM - actions with real consequences (approve/reject/apply/
    maintenance) are never left to a model's interpretation, only exact
    pattern matches execute. Returns a reply string if this was a command,
    None if it wasn't (falls through to normal chat)."""
    lower = msg.lower().strip()
    id_match = JOB_ID_RE.search(msg)
    job_id = id_match.group(1) if id_match else None

    if lower.startswith("approve"):
        jid = job_id or latest_job_id()
        if not jid:
            return "No job found to approve."
        r = post_json(f"{MAIN}/job/review", {"job_id": jid, "decision": "approved"})
        return f"Approved {jid}." if r.get("ok") else f"Failed: {r.get('error')}"

    if lower.startswith("reject"):
        jid = job_id or latest_job_id()
        if not jid:
            return "No job found to reject."
        r = post_json(f"{MAIN}/job/review", {"job_id": jid, "decision": "rejected"})
        return f"Rejected {jid}." if r.get("ok") else f"Failed: {r.get('error')}"

    if lower.startswith("apply"):
        secret_match = re.search(r"secret[: ]+([A-Za-z0-9_\-]{15,})", msg, re.IGNORECASE)
        if not secret_match:
            return "To apply, include the admin secret, e.g. 'apply job_xxx secret YOURSECRET'."
        jid = job_id or latest_job_id()
        if not jid:
            return "No job found to apply."
        r = post_json(f"{MAIN}/job/apply", {"job_id": jid, "admin_secret": secret_match.group(1)})
        return r.get("message") if r.get("ok") else f"Failed: {r.get('error')}"

    if "stop maintenance" in lower:
        post_json(f"{MAIN}/maintenance/stop", {})
        return "Maintenance stopped, back to normal."

    if "start maintenance" in lower:
        mins_match = re.search(r"(\d+)\s*min", lower)
        duration = int(mins_match.group(1)) * 60 if mins_match else None
        msg_match = re.search(r":\s*(.+)$", msg)
        message = msg_match.group(1).strip() if msg_match else "Thunder's down for maintenance, back shortly."
        post_json(f"{MAIN}/maintenance/start", {"message": message, "duration_seconds": duration})
        when = f"{mins_match.group(1)} min" if mins_match else "indefinitely"
        return f"Maintenance started for {when}: {message}"

    return None


def odris_chat(message: str) -> str:
    overview = build_overview()
    context = (
        f"Live system snapshot:\n"
        f"Thunder-Main status: {json.dumps(overview['status'])}\n"
        f"Node heartbeat: {json.dumps(overview['heartbeat'])}\n"
        f"Recent jobs: {json.dumps([{k: j.get(k) for k in ('id','title','status','review_status')} for j in overview['jobs']])}\n"
        f"Recent errors: {json.dumps([{k: e.get(k) for k in ('id','endpoint','error','review_status')} for e in overview['errors']])}\n\n"
        f"Blayne's question: {message}"
    )
    payload = {
        "model": get_json(f"{MAIN}/status").get("model", "dolphin3"),
        "stream": False,
        "messages": [
            {"role": "system", "content": ODRIS_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    }
    body = post_json(f"{OLLAMA}/api/chat", payload, timeout=120)
    return body.get("message", {}).get("content") or json.dumps(body)


class Handler(BaseHTTPRequestHandler):
    grant_session = False

    def _send(self, code, obj, content_type="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode() if content_type == "application/json" else obj.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if self.grant_session:
            # HttpOnly and SameSite: the page never needs to read this, and no
            # other site should be able to make the browser send it.
            self.send_header("Set-Cookie",
                             f"odris_session={SESSION_TOKEN}; Path=/; "
                             f"HttpOnly; SameSite=Strict; Max-Age=86400")
            self.grant_session = False
        self.end_headers()
        self.wfile.write(body)

    def _require_auth(self) -> bool:
        if check_auth(self):
            return True
        body = json.dumps({"error": "auth required"}).encode()
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Thunder Admin"')
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def do_GET(self):
        if not self._require_auth():
            return
        if self.path == "/":
            return self._send(200, PAGE, content_type="text/html")
        if self.path == "/api/overview":
            return self._send(200, build_overview())
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._require_auth():
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})

        if self.path == "/api/chat":
            msg = (body.get("message") or "").strip()
            if not msg:
                return self._send(400, {"error": "missing message"})
            try:
                cmd_reply = parse_and_execute_command(msg)
                if cmd_reply is not None:
                    return self._send(200, {"reply": cmd_reply})
                return self._send(200, {"reply": odris_chat(msg)})
            except Exception as e:
                return self._send(502, {"reply": f"Odris couldn't reach Main: {e}"})

        if self.path == "/api/job/review":
            try:
                return self._send(200, post_json(f"{MAIN}/job/review", body))
            except Exception as e:
                return self._send(502, {"error": str(e)})

        if self.path == "/api/job/apply":
            try:
                return self._send(200, post_json(f"{MAIN}/job/apply", body, timeout=15))
            except Exception as e:
                return self._send(502, {"error": str(e)})

        if self.path.startswith("/api/errors/") and self.path.endswith("/fix"):
            error_id = self.path.split("/")[3]
            try:
                return self._send(200, post_json(f"{MAIN}/errors/{error_id}/fix", {}))
            except Exception as e:
                return self._send(502, {"error": str(e)})

        if self.path == "/api/maintenance/start":
            try:
                return self._send(200, post_json(f"{MAIN}/maintenance/start", body))
            except Exception as e:
                return self._send(502, {"error": str(e)})

        if self.path == "/api/maintenance/stop":
            try:
                return self._send(200, post_json(f"{MAIN}/maintenance/stop", {}))
            except Exception as e:
                return self._send(502, {"error": str(e)})

        return self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Odris admin dashboard listening on :{PORT}")
    server.serve_forever()
