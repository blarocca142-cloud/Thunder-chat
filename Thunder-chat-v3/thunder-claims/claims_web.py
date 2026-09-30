#!/usr/bin/env python3
"""Thunder Claims - the claim screen, in a browser.

The pieces already worked from the command line: OCR, extraction, repair,
validation, the encrypted vault. Nobody bills from a command line, so this
puts them behind one screen:

- claims, laid out in CMS-1500 box order, checked as you type
- a patient list, and saved insurers and providers, so a claim is picked
  together rather than retyped
- tracking: sent, paid, partly paid, denied, with amounts and a balance
- a printable CMS-1500-style page for review and the paper file

Everything - claims, patients, insurers, providers - is a record in the
encrypted vault. Nothing is ever submitted to a payer from here.

Security, because these are patient records:
- TLS with the fleet's own CA (the same certificate as Main's :8443); it
  refuses to listen off loopback without it
- one login per person, scrypt-hashed, never a shared password; lockout after
  5 wrong tries; automatic logoff after 15 idle minutes
- every request logged to <vault>/access.log with who, where from and what
  (record ids only), and every record read/write to the vault's audit log
  under the person's name, not the Unix account's

    ./claims_web.py adduser blayne       # manage logins (also: users, passwd,
                                         #   disable, enable)
    ./claims_web.py                      # this machine only, http://127.0.0.1:8770
    ./claims_web.py --host 10.168.168.10 --tls-cert server.crt --tls-key server.key

The desktop program (desktop/) is the front end the office uses; it trusts
only the fleet CA. Standard library only, so it runs wherever the vault does.

Synthetic patients only until Blayne says otherwise.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import ssl
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import intake  # noqa: E402  (brings vault, extract, repair, validate, codelist)
from intake import codelist, vault  # noqa: E402

PAGE = HERE / "claims_web.html"
MAX_UPLOAD = 25 * 1024 * 1024
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Every kind of record lives in the one vault, told apart by id prefix. Claims
# kept the bare "c" prefix they were first saved with.
KINDS = {
    "claim":    {"prefix": "c",    "index": ["patient_name", "claim_number"]},
    "patient":  {"prefix": "pt-",  "index": ["patient_name"]},
    "payer":    {"prefix": "ins-", "index": []},
    "provider": {"prefix": "pv-",  "index": []},
}
BILLING = ("draft", "sent", "hold", "paid", "partial", "denied")
FIRST_ACCOUNT = 1000  # EZClaim numbers patients from 1000 up


def kind_of(record_id: str) -> str:
    for k in ("patient", "payer", "provider"):
        if record_id.startswith(KINDS[k]["prefix"]):
            return k
    return "claim"


def money(v) -> float:
    try:
        return round(float(str(v or "0").replace("$", "").replace(",", "")), 2)
    except ValueError:
        return 0.0


def total_charges(claim: dict) -> float:
    t = 0.0
    for p in claim.get("procedures") or []:
        units = money((p or {}).get("units")) or 1
        t += units * money((p or {}).get("charge"))
    return round(t, 2)


def assess(claim: dict) -> dict:
    """Everything the form shows next to the claim: the triage pile, the
    reasons, and whether each code is on the official list."""
    issues = intake.check(claim)
    status, reasons = intake.triage(issues, [], claim)
    codes = {}
    for dx in claim.get("diagnoses") or []:
        c = str((dx or {}).get("code") or "").strip()
        if c:
            codes[c] = codelist.icd10_exists(c)
    for pr in claim.get("procedures") or []:
        c = str((pr or {}).get("code") or "").strip()
        if c:
            codes[c] = codelist.procedure_exists(c)
    return {"status": status, "reasons": reasons, "issues": issues, "codes": codes}


def summary(kind: str, rid: str, r: dict) -> dict:
    if kind == "claim":
        meta = r.get("_meta") or {}
        track = r.get("tracking") or {}
        charges = total_charges(r)
        paid = money(track.get("paid_amount"))
        return {"id": rid, "patient_name": r.get("patient_name", ""),
                "account_number": r.get("account_number", ""),
                "patient_id": r.get("patient_id", ""),
                "date_of_service": r.get("date_of_service", ""),
                "insurer": r.get("insurer", ""), "status": meta.get("status", ""),
                "billing": track.get("billing") or "draft",
                "charges": charges, "paid": paid, "balance": round(charges - paid, 2),
                "saved": meta.get("saved", "")}
    if kind == "patient":
        return {"id": rid, "patient_name": r.get("patient_name", ""), "dob": r.get("dob", ""),
                "insurer": r.get("insurer", ""), "phone": r.get("phone", ""),
                "account_number": r.get("account_number", ""),
                "active": r.get("active", True) is not False,
                "address": r.get("address", ""), "city": r.get("city", ""),
                "state": r.get("state", ""), "zip": r.get("zip", ""),
                "email": r.get("email", ""), "insured_id": r.get("claim_number", ""),
                "insurer2": r.get("insurer2", ""), "insured_id2": r.get("insured_id2", ""),
                "reminder": r.get("reminder", "")}
    if kind == "payer":
        return {"id": rid, "name": r.get("name", ""), "payer_id": r.get("payer_id", ""),
                "phone": r.get("phone", "")}
    return {"id": rid, "name": r.get("name", ""), "npi": r.get("npi", ""),
            "role": r.get("role", ""), "tax_id": r.get("tax_id", "")}


def list_records(kind: str) -> list[dict]:
    """Every record of one kind, newest first. Each one is decrypted (and
    audited) to show its name - the cost of a list a person can read."""
    out = []
    for p in sorted(vault.records_dir().glob("*.rec"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        if kind_of(p.stem) != kind:
            continue
        try:
            r = vault.get(p.stem)
        except BaseException as e:  # vault raises SystemExit on a bad record
            out.append({"id": p.stem, "error": str(e).splitlines()[0]})
            continue
        out.append(summary(kind, p.stem, r))
    return out


def new_id(kind: str) -> str:
    return KINDS[kind]["prefix"] + time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2)


def next_account_number() -> str:
    """One more than the highest account number on file, EZClaim-style."""
    top = FIRST_ACCOUNT - 1
    for p in list_records("patient"):
        try:
            top = max(top, int(str(p.get("account_number") or "").strip()))
        except ValueError:
            pass
    return str(top + 1)


def note(text: str, user: str, balance: float) -> dict:
    return {"ts": time.strftime("%m/%d/%Y %I:%M %p"), "user": user.upper(),
            "note": text, "balance": round(balance, 2)}


def save(kind: str, record_id: str | None, data: dict, user: str = "user") -> dict:
    if kind not in KINDS:
        raise ValueError("unknown record type")
    rid = record_id or new_id(kind)
    if not ID_RE.match(rid) or kind_of(rid) != kind:
        raise ValueError("bad record id")
    data = {k: v for k, v in data.items() if k != "_meta"}
    extra = {}
    if kind == "claim":
        track = data.get("tracking") or {}
        if track.get("billing") and track["billing"] not in BILLING:
            raise ValueError("unknown billing status")
        a = assess(data)
        log = [n for n in (data.get("notes_log") or []) if isinstance(n, dict)]
        log.append(note("Claim edited" if record_id else "Claim created.", user,
                        total_charges(data) - money(track.get("paid_amount"))))
        data["notes_log"] = log
        data["_meta"] = {"status": a["status"], "reasons": a["reasons"],
                         "saved": time.strftime("%Y-%m-%d %H:%M")}
        extra = a
    else:
        if kind == "patient":
            last, first, mi = (str(data.get(k) or "").strip() for k in ("last_name", "first_name", "mi"))
            if last or first:
                data["patient_name"] = (last + ", " + first + (" " + mi if mi else "")).upper().strip(", ")
            if not str(data.get("account_number") or "").strip():
                data["account_number"] = next_account_number()
        name = data.get("patient_name") if kind == "patient" else data.get("name")
        if not str(name or "").strip():
            raise ValueError("a name is required")
    vault.put(rid, data, KINDS[kind]["index"])
    return {"id": rid, "data": data, **extra}


def scan(data: bytes, filename: str) -> dict:
    """A scanned page in, a pre-filled claim out. The upload lives in a temp
    file only as long as tesseract needs it, and the extraction is returned to
    the page, not written anywhere."""
    suffix = Path(filename or "scan.png").suffix.lower() or ".png"
    if suffix not in intake.IMAGES | intake.PDFS:
        raise ValueError("send a photo (.png, .jpg, .tif) or a PDF")
    fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="claims_scan_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        text = intake.ocr_document(Path(tmp))
    finally:
        os.unlink(tmp)
    if len(text.strip()) < 20:
        raise ValueError("couldn't read any text on that page - try a sharper, straighter photo")
    claim = intake.extract(text)
    claim, repairs = intake.repair_claim(claim)
    return {"claim": claim, "repairs": repairs, **assess(claim)}


# --------------------------------------------------------------------------
# accounts and sessions
# --------------------------------------------------------------------------
# One login per person, never a shared password: the audit log is only worth
# anything if it can say *who*. Passwords are scrypt-hashed; sessions live in
# memory only, so a restart logs everyone out rather than leaving tokens on disk.

USERS_FILE = Path(os.environ.get("THUNDER_CLAIMS_USERS",
                                 str(Path.home() / ".thunder" / "claims_users.json")))
MIN_PASSWORD = 12
IDLE_SECONDS = 15 * 60          # automatic logoff after 15 idle minutes
MAX_SESSION_SECONDS = 12 * 3600  # and after 12 hours regardless
MAX_FAILURES = 5                # wrong passwords before a lockout
LOCKOUT_SECONDS = 15 * 60
NAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,31}$")
_SCRYPT = {"n": 2 ** 15, "r": 8, "p": 1, "maxmem": 64 * 1024 * 1024, "dklen": 32}


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)


def load_users() -> dict:
    try:
        return json.loads(USERS_FILE.read_text())
    except FileNotFoundError:
        return {}


def save_users(users: dict) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(users, f, indent=2)
    os.replace(tmp, USERS_FILE)


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD:
        return f"use at least {MIN_PASSWORD} characters"
    if len(set(password)) < 5:
        return "too repetitive"
    return None


def set_password(name: str, password: str, role: str = "user") -> None:
    name = name.strip().lower()
    if not NAME_RE.match(name):
        raise ValueError("user names are lower-case letters, digits, . _ - (2-32 long)")
    problem = password_problem(password)
    if problem:
        raise ValueError("password rejected: " + problem)
    users = load_users()
    salt = secrets.token_bytes(16)
    u = users.get(name, {"role": role, "created": time.strftime("%Y-%m-%d %H:%M")})
    u.update({"salt": base64.b64encode(salt).decode(), "hash": base64.b64encode(_hash(password, salt)).decode(),
              "kdf": "scrypt-32768-8-1", "changed": time.strftime("%Y-%m-%d %H:%M")})
    u.setdefault("disabled", False)
    users[name] = u
    save_users(users)


_DUMMY_SALT = secrets.token_bytes(16)


def verify_password(name: str, password: str) -> bool:
    u = load_users().get(name.strip().lower())
    if not u or u.get("disabled"):
        _hash(password, _DUMMY_SALT)  # same cost either way: no user-exists oracle by timing
        return False
    want = base64.b64decode(u["hash"])
    return hmac.compare_digest(_hash(password, base64.b64decode(u["salt"])), want)


class Sessions:
    def __init__(self):
        self.lock = threading.Lock()
        self.live: dict[str, dict] = {}
        self.fails: dict[str, list] = {}   # key -> [count, locked_until]

    def locked(self, *keys: str) -> int:
        now = time.time()
        with self.lock:
            return max([int(self.fails.get(k, [0, 0])[1] - now) for k in keys] + [0])

    def failed(self, *keys: str) -> None:
        now = time.time()
        with self.lock:
            for k in keys:
                f = self.fails.setdefault(k, [0, 0])
                f[0] += 1
                if f[0] >= MAX_FAILURES:
                    f[0], f[1] = 0, now + LOCKOUT_SECONDS

    def start(self, user: str, *keys: str) -> str:
        tok = secrets.token_urlsafe(32)
        now = time.time()
        with self.lock:
            for k in keys:
                self.fails.pop(k, None)
            self.live[tok] = {"user": user, "created": now, "last": now}
        return tok

    def touch(self, tok: str) -> str | None:
        now = time.time()
        with self.lock:
            s = self.live.get(tok)
            if not s:
                return None
            if now - s["last"] > IDLE_SECONDS or now - s["created"] > MAX_SESSION_SECONDS:
                del self.live[tok]
                return None
            u = load_users().get(s["user"])
            if not u or u.get("disabled"):
                del self.live[tok]
                return None
            s["last"] = now
            return s["user"]

    def end(self, tok: str) -> None:
        with self.lock:
            self.live.pop(tok, None)


SESSIONS = Sessions()


def access_log(who: str, ip: str, method: str, path: str, status: int) -> None:
    """Who asked for what, from where. Record ids only - no names, so the log
    is not itself PHI."""
    line = json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "who": who, "ip": ip,
                       "method": method, "path": path[:200], "status": status})
    path_ = vault.VAULT / "access.log"
    fd = os.open(path_, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as f:
        f.write(line + "\n")


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

PUBLIC = {("GET", "/"), ("GET", "/index.html"), ("POST", "/api/login")}
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class Handler(BaseHTTPRequestHandler):
    server_version = "ThunderClaims/3"
    sys_version = ""
    timeout = 30        # a stalled client cannot hold a thread forever
    tls = False

    def setup(self):
        if isinstance(self.request, ssl.SSLSocket):
            self.request.settimeout(15)
            self.request.do_handshake()
        super().setup()

    def log_message(self, fmt, *args):  # no request lines on stdout
        pass

    def _send(self, code: int, body, ctype="application/json", extra: dict | None = None):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self._status = code
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)
        if self.tls:
            self.send_header("Strict-Transport-Security", "max-age=31536000")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD:
            raise ValueError("file too large (25 MB max)")
        return self.rfile.read(n)

    def _token(self) -> str:
        h = self.headers.get("Authorization", "")
        return h[7:].strip() if h.lower().startswith("bearer ") else ""

    def _handle(self, method: str):
        u = urlparse(self.path)
        ip = self.client_address[0]
        self._status, who = 0, "anonymous"
        try:
            if (method, u.path) not in PUBLIC:
                who = SESSIONS.touch(self._token()) or ""
                if not who:
                    who = "anonymous"
                    return self._send(401, {"error": "login required"})
            vault.set_actor(who)
            (self._get if method == "GET" else self._post)(u, who, ip)
        except ValueError as e:
            self._send(400, {"error": str(e)})
        except BaseException as e:
            self._send(500, {"error": str(e).splitlines()[0] if str(e) else type(e).__name__})
        finally:
            vault.set_actor(None)
            if u.path not in ("/", "/index.html"):
                access_log(who, ip, method, u.path + ("?" + u.query if u.query else ""), self._status)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def _get(self, u, who, ip):
        if u.path in ("/", "/index.html"):
            return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/whoami":
            return self._send(200, {"user": who, "idle_minutes": IDLE_SECONDS // 60})
        if u.path == "/api/list":
            kind = (parse_qs(u.query).get("kind") or ["claim"])[0]
            if kind not in KINDS:
                return self._send(400, {"error": "unknown record type"})
            return self._send(200, {"records": list_records(kind)})
        m = re.match(r"^/api/rec/([A-Za-z0-9_-]+)$", u.path)
        if m:
            rid = m.group(1)
            r = vault.get(rid)
            kind = kind_of(rid)
            body = {"id": rid, "kind": kind, "data": r}
            if kind == "claim":
                body.update(assess(r))
            return self._send(200, body)
        self._send(404, {"error": "not found"})

    def _post(self, u, who, ip):
        if u.path == "/api/login":
            b = json.loads(self._body() or b"{}")
            name = str(b.get("user") or "").strip().lower()[:32]
            wait = SESSIONS.locked("u:" + name, "ip:" + ip)
            if wait:
                return self._send(429, {"error": f"Too many wrong passwords. Locked for {wait // 60 + 1} more minutes."})
            if not verify_password(name, str(b.get("password") or "")):
                SESSIONS.failed("u:" + name, "ip:" + ip)
                return self._send(401, {"error": "Wrong user name or password."})
            tok = SESSIONS.start(name, "u:" + name, "ip:" + ip)
            vault.set_actor(name)
            return self._send(200, {"token": tok, "user": name, "idle_minutes": IDLE_SECONDS // 60})
        if u.path == "/api/logout":
            SESSIONS.end(self._token())
            return self._send(200, {"ok": True})
        if u.path == "/api/check":
            return self._send(200, assess(json.loads(self._body() or b"{}")))
        if u.path == "/api/save":
            b = json.loads(self._body() or b"{}")
            return self._send(200, save(b.get("kind") or "", b.get("id"), b.get("data") or {}, who))
        if u.path == "/api/scan":
            return self._send(200, scan(self._body(), self.headers.get("X-Filename", "")))
        self._send(404, {"error": "not found"})


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass  # failed handshakes and dropped clients are not worth a traceback


def bootstrap_owner() -> None:
    """First run after the move from one shared password to per-person
    logins: the old password becomes blayne's, so nothing breaks on upgrade."""
    old = os.environ.get("THUNDER_CLAIMS_PASSWORD")
    if load_users() or not old:
        return
    try:
        set_password("blayne", old, role="owner")
        print("Created user 'blayne' from THUNDER_CLAIMS_PASSWORD.")
    except ValueError as e:
        print(f"Could not create 'blayne' from THUNDER_CLAIMS_PASSWORD ({e}). Run: {sys.argv[0]} adduser blayne")


def ask_password() -> str:
    pw = os.environ.get("CLAIMS_NEW_PASSWORD")
    if pw:
        return pw
    a, b = getpass.getpass("new password: "), getpass.getpass("again: ")
    if a != b:
        raise SystemExit("the two passwords did not match")
    return a


def accounts(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="claims_web.py", description="Manage Thunder Claims logins.")
    ap.add_argument("cmd", choices=["users", "adduser", "passwd", "disable", "enable"])
    ap.add_argument("name", nargs="?")
    a = ap.parse_args(argv)
    users = load_users()
    if a.cmd == "users":
        for n, u in sorted(users.items()):
            print(f"{n:16} {u.get('role', 'user'):6} {'DISABLED' if u.get('disabled') else 'active':8} changed {u.get('changed', '?')}")
        if not users:
            print("no users yet")
        return 0
    if not a.name:
        raise SystemExit("which user?")
    name = a.name.lower()
    if a.cmd in ("adduser", "passwd"):
        if a.cmd == "adduser" and name in users:
            raise SystemExit(f"{name} already exists - use passwd")
        if a.cmd == "passwd" and name not in users:
            raise SystemExit(f"no user {name}")
        try:
            set_password(name, ask_password(), role="owner" if not users else "user")
        except ValueError as e:
            raise SystemExit(str(e))
        print(("added " if a.cmd == "adduser" else "changed password for ") + name)
        return 0
    if name not in users:
        raise SystemExit(f"no user {name}")
    users[name]["disabled"] = a.cmd == "disable"
    save_users(users)
    print(f"{name} {'disabled - logged out on their next request' if a.cmd == 'disable' else 'enabled'}")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("users", "adduser", "passwd", "disable", "enable"):
        return accounts(sys.argv[1:])
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--tls-cert", help="server certificate (the fleet CA's, thunder-data/tls/server.crt)")
    ap.add_argument("--tls-key", help="server private key")
    a = ap.parse_args()
    loopback = a.host in ("127.0.0.1", "localhost", "::1")
    if not loopback and not (a.tls_cert and a.tls_key):
        print("Refusing to serve patient records on the network without TLS.\n"
              "Pass --tls-cert and --tls-key, or leave --host at 127.0.0.1.")
        return 2
    try:
        vault.keys_load()
    except SystemExit as e:
        print(f"Vault not ready: {e}")
        return 2
    bootstrap_owner()
    if not loopback and not load_users():
        print(f"No logins exist yet. Create one first:  {sys.argv[0]} adduser <name>")
        return 2
    srv = Server((a.host, a.port), Handler)
    scheme = "http"
    if a.tls_cert and a.tls_key:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(a.tls_cert, a.tls_key)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True, do_handshake_on_connect=False)
        Handler.tls, scheme = True, "https"
    print(f"Thunder Claims on {scheme}://{a.host}:{a.port}/  (login required; "
          f"auto-logoff after {IDLE_SECONDS // 60} idle minutes)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
