"""Odris tool gate: every tool Thunder uses is asked for here first.

Thunder's model decides it wants a tool; Main asks Odris; Odris says yes or no,
writes it down, and - for anything that touches the internet - does the work
itself, because Odris is the only machine in the fleet allowed out.

What "kosher" means, concretely:

  * Allowlist. A tool not named in TOOLS does not exist, whatever the model
    asks for.
  * Argument checks. Types, lengths, and per-tool rules (http/https only, no
    LAN addresses, no local file paths).
  * Nothing medical leaves the house. Anything bound for the internet is
    scanned for things that look like patient data - SSNs, dates of birth,
    member IDs, ICD-10 codes, NPIs - and refused if it matches. A false refusal
    costs a retyped search; a false pass could be a HIPAA breach.
  * No reaching back in. fetch_url resolves the host and refuses private,
    loopback and link-local addresses, so a web page cannot trick Thunder into
    reading the fleet's own admin endpoints.
  * Rate limits, so a model stuck in a loop cannot hammer anything.
  * Every decision logged, allowed or not, one JSON line each.

Stdlib only, same as the other Odris services. Fails closed: Main treats "no
answer from Odris" as "no".
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odris_websearch import web_search  # noqa: E402

PORT = int(os.environ.get("ODRIS_GATE_PORT", "9007"))
LOG = Path(os.environ.get("ODRIS_GATE_LOG", str(Path.home() / "thunder-gate" / "gate.log")))
UA = "Mozilla/5.0 (compatible; ThunderOdrisGate/1.0)"
FETCH_MAX_BYTES = 2_000_000
FETCH_MAX_CHARS = 12_000

# Only Main may ask. Anything else on the LAN gets a refusal and a log line.
ALLOWED_CALLERS = {
    c.strip() for c in os.environ.get("ODRIS_GATE_CALLERS", "10.168.168.10,127.0.0.1").split(",") if c.strip()
}

# name -> (runs where, calls per minute, argument spec)
# "odris" tools are executed here. "main" tools are executed on Main after
# Odris approves them; Odris still checks and logs them.
TOOLS: dict[str, dict] = {
    "web_search":   {"runs": "odris", "per_min": 20, "args": {"query": (str, 1, 300)}},
    "fetch_url":    {"runs": "odris", "per_min": 20, "args": {"url": (str, 8, 2000)}},
    "run_python":   {"runs": "main",  "per_min": 30, "args": {"code": (str, 1, 40_000)}},
    "forge_code":   {"runs": "main",  "per_min": 6,   "args": {"task": (str, 1, 20_000)}},
    "read_file":    {"runs": "main",  "per_min": 60, "args": {"path": (str, 1, 300)}},
    "write_file":   {"runs": "main",  "per_min": 30, "args": {"path": (str, 1, 300), "content": (str, 0, 200_000)}},
    "list_files":   {"runs": "main",  "per_min": 60, "args": {"path": (str, 0, 300)}},
    "memory_search": {"runs": "main", "per_min": 60, "args": {"query": (str, 1, 500)}},
    "system_status": {"runs": "main", "per_min": 20, "args": {}},
}
OUTBOUND = {"web_search", "fetch_url"}

# Patterns that look like patient data. Deliberately broad.
PHI_PATTERNS = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("SSN", re.compile(r"\bssn\b|\bsocial security\b", re.I)),
    ("date of birth", re.compile(r"\b(dob|d\.o\.b|date of birth|birth ?date)\b", re.I)),
    ("date", re.compile(r"\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](19|20)\d{2}\b")),
    ("member/policy ID", re.compile(r"\b(member|policy|subscriber|patient|mrn|claim)\s*(id|#|no\.?|number)\b", re.I)),
    ("NPI", re.compile(r"\bnpi\b", re.I)),
    ("ICD-10 code", re.compile(r"\b[A-TV-Z][0-9][0-9AB](\.[0-9A-TV-Z]{1,4})\b")),
    ("patient", re.compile(r"\bpatient\b.*\b(name|named|called)\b", re.I)),
]

_lock = threading.Lock()
_calls: dict[str, deque] = {name: deque() for name in TOOLS}


def log(entry: dict) -> None:
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with _lock, LOG.open("a") as f:
        f.write(json.dumps(entry)[:4000] + "\n")


def phi_hits(text: str) -> list[str]:
    return sorted({label for label, pat in PHI_PATTERNS if pat.search(text)})


def check_args(tool: str, args: dict) -> str | None:
    spec = TOOLS[tool]["args"]
    if not isinstance(args, dict):
        return "arguments must be an object"
    extra = set(args) - set(spec)
    if extra:
        return f"unknown arguments: {', '.join(sorted(extra))}"
    for name, (typ, lo, hi) in spec.items():
        if name not in args:
            if lo == 0:
                continue
            return f"missing argument: {name}"
        val = args[name]
        if not isinstance(val, typ):
            return f"{name} must be {typ.__name__}"
        if isinstance(val, str) and not (lo <= len(val) <= hi):
            return f"{name} must be {lo}-{hi} characters"
    return None


def rate_ok(tool: str) -> bool:
    now = time.time()
    with _lock:
        q = _calls[tool]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= TOOLS[tool]["per_min"]:
            return False
        q.append(now)
        return True


def public_http_url(url: str) -> str | None:
    """None if the URL is safe to fetch from the internet, else the reason."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "unparseable URL"
    if parts.scheme not in ("http", "https"):
        return "only http and https"
    host = parts.hostname
    if not host:
        return "no host"
    if parts.username or parts.password:
        return "credentials in URL"
    try:
        infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror:
        return "host does not resolve"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            return f"{host} is a private or local address"
    return None


def decide(tool: str, args: dict, caller: str) -> tuple[bool, str]:
    if caller not in ALLOWED_CALLERS:
        return False, f"caller {caller} is not allowed to use tools"
    if tool not in TOOLS:
        return False, f"no such tool: {tool}"
    problem = check_args(tool, args)
    if problem:
        return False, problem
    if tool in OUTBOUND:
        hits = phi_hits(" ".join(str(v) for v in args.values()))
        if hits:
            return False, ("refused: this would send something that looks like patient data "
                           f"({', '.join(hits)}) to the internet")
    if tool == "fetch_url":
        problem = public_http_url(args["url"])
        if problem:
            return False, f"refused: {problem}"
    if not rate_ok(tool):
        return False, f"rate limit: {tool} is capped at {TOOLS[tool]['per_min']} calls a minute"
    return True, "ok"


class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "pre", "section", "article"}

    def __init__(self):
        super().__init__()
        self.out: list[str] = []
        self.skip = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            self.out.append(data)

    def text(self) -> str:
        raw = "".join(self.out)
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n\n", raw)
        return raw.strip()


class NoRedirectToPrivate(urllib.request.HTTPRedirectHandler):
    """A public page must not be able to redirect the fetch onto the LAN."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        problem = public_http_url(newurl)
        if problem:
            raise urllib.error.URLError(f"redirect refused: {problem}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_url(url: str) -> dict:
    opener = urllib.request.build_opener(NoRedirectToPrivate)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain,*/*"})
    with opener.open(req, timeout=15) as r:
        ctype = r.headers.get("Content-Type", "")
        blob = r.read(FETCH_MAX_BYTES)
        final = r.geturl()
    if not any(t in ctype for t in ("text/", "json", "xml")):
        return {"url": final, "title": "", "text": f"(not a text page: {ctype or 'unknown type'})"}
    html = blob.decode("utf-8", errors="ignore")
    if "html" in ctype:
        p = TextExtractor()
        p.feed(html)
        title, text = p.title.strip(), p.text()
    else:
        title, text = "", html
    truncated = len(text) > FETCH_MAX_CHARS
    return {"url": final, "title": title, "text": text[:FETCH_MAX_CHARS], "truncated": truncated}


def execute(tool: str, args: dict) -> dict:
    if tool == "web_search":
        return {"results": web_search(args["query"], 6)}
    if tool == "fetch_url":
        return fetch_url(args["url"])
    raise ValueError(tool)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "tools": sorted(TOOLS)})
        if self.path == "/tools":
            return self._send(200, {n: {"runs": t["runs"], "per_min": t["per_min"]} for n, t in TOOLS.items()})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/tool":
            return self._send(404, {"error": "not found"})
        caller = self.client_address[0]
        try:
            length = min(int(self.headers.get("Content-Length", 0)), 400_000)
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"allowed": False, "reason": "bad json"})
        tool = str(body.get("tool", ""))
        args = body.get("args") or {}
        allowed, reason = decide(tool, args, caller)
        entry = {"caller": caller, "tool": tool, "allowed": allowed, "reason": reason,
                 "args": {k: (v[:200] if isinstance(v, str) else v) for k, v in args.items()}
                 if isinstance(args, dict) else str(args)[:200]}
        if not allowed:
            log(entry)
            return self._send(200, {"allowed": False, "reason": reason})
        if TOOLS[tool]["runs"] == "main":
            log(entry)
            return self._send(200, {"allowed": True, "runs": "main"})
        try:
            result = execute(tool, args)
            entry["ok"] = True
            log(entry)
            return self._send(200, {"allowed": True, "runs": "odris", "result": result})
        except Exception as e:
            entry.update(ok=False, error=str(e)[:300])
            log(entry)
            return self._send(200, {"allowed": True, "runs": "odris", "error": str(e)[:300]})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Odris tool gate listening on :{PORT}, callers {sorted(ALLOWED_CALLERS)}")
    server.serve_forever()
