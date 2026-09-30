#!/usr/bin/env python3
"""Security checks for the claims server, run against the real thing over TLS.

A throwaway CA and server certificate are made with openssl, a scratch vault
and users file are used, and the server runs on a loopback port in a thread.
Mostly attacks: no login, wrong password, lockout, idle expiry, disabled
user, reused token after logout, wrong CA, plaintext to the TLS port.

    python3 test_claims_web.py
"""
import http.client
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="claims_web_test_"))
os.environ["THUNDER_VAULT"] = str(TMP / "vault")
os.environ["THUNDER_VAULT_KEY"] = str(TMP / "vault.key")
os.environ["THUNDER_CLAIMS_USERS"] = str(TMP / "users.json")
os.environ.pop("THUNDER_CLAIMS_PASSWORD", None)
sys.path.insert(0, str(Path(__file__).parent))

import vault  # noqa: E402
import claims_web as cw  # noqa: E402

PASSED = FAILED = 0


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  pass  {name}")
    else:
        FAILED += 1
        print(f"  FAIL  {name}  {detail}")


def sh(*args):
    subprocess.run(args, check=True, capture_output=True)


def make_ca(d: Path, cn: str):
    sh("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(d / "ca.key"),
       "-out", str(d / "ca.crt"), "-days", "2", "-subj", f"/CN={cn}",
       "-addext", "basicConstraints=critical,CA:TRUE")


d = TMP / "tls"; d.mkdir()
make_ca(d, "Test Fleet CA")
sh("openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", str(d / "server.key"),
   "-out", str(d / "server.csr"), "-subj", "/CN=localhost")
(d / "ext.cnf").write_text("subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=CA:FALSE\n")
sh("openssl", "x509", "-req", "-in", str(d / "server.csr"), "-CA", str(d / "ca.crt"), "-CAkey", str(d / "ca.key"),
   "-CAcreateserial", "-out", str(d / "server.crt"), "-days", "2", "-extfile", str(d / "ext.cnf"))
other = TMP / "other"; other.mkdir()
make_ca(other, "Some Other CA")

if not Path(os.environ["THUNDER_VAULT_KEY"]).exists():
    subprocess.run([sys.executable, str(Path(__file__).parent / "vault.py"), "init"], check=True,
                   capture_output=True, env=os.environ)

print("accounts")
for bad, why in (("short", "too short"), ("aaaaaaaaaaaaaaaa", "repetitive")):
    try:
        cw.set_password("blayne", bad)
        check(f"rejects a {why} password", False)
    except ValueError:
        check(f"rejects a {why} password", True)
try:
    cw.set_password("Bad Name!", "correct horse battery")
    check("rejects a malformed user name", False)
except ValueError:
    check("rejects a malformed user name", True)
PW = "correct horse battery staple"
cw.set_password("blayne", PW, role="owner")
cw.set_password("dad", "another long passphrase 9")
stored = (TMP / "users.json").read_text()
check("password is not stored in the clear", PW not in stored)
check("users file is mode 600", oct((TMP / "users.json").stat().st_mode & 0o777) == "0o600")
check("verify: right password", cw.verify_password("blayne", PW))
check("verify: wrong password", not cw.verify_password("blayne", PW + "x"))
check("verify: unknown user", not cw.verify_password("nobody", PW))

# --- run the server over TLS on a free loopback port
sock = socket.socket(); sock.bind(("127.0.0.1", 0)); PORT = sock.getsockname()[1]; sock.close()
srv = cw.Server(("127.0.0.1", PORT), cw.Handler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.minimum_version = ssl.TLSVersion.TLSv1_2
ctx.load_cert_chain(str(d / "server.crt"), str(d / "server.key"))
srv.socket = ctx.wrap_socket(srv.socket, server_side=True, do_handshake_on_connect=False)
cw.Handler.tls = True
threading.Thread(target=srv.serve_forever, daemon=True).start()

client_ctx = ssl.create_default_context(cafile=str(d / "ca.crt"))


def req(method, path, body=None, token=None, ctx_=None):
    c = http.client.HTTPSConnection("localhost", PORT, context=ctx_ or client_ctx, timeout=10)
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    c.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
    r = c.getresponse()
    data = r.read()
    try:
        j = json.loads(data)
    except ValueError:
        j = {}
    return r.status, j, dict(r.getheaders())


print("transport")
try:
    req("GET", "/", ctx_=ssl.create_default_context(cafile=str(other / "ca.crt")))
    check("a client trusting a different CA is refused", False)
except ssl.SSLError:
    check("a client trusting a different CA is refused", True)
try:
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
    c.request("GET", "/api/list?kind=claim")
    check("plaintext http to the TLS port gets nothing", c.getresponse().status not in (200,))
except (ConnectionError, http.client.HTTPException, OSError):
    check("plaintext http to the TLS port gets nothing", True)
st, _, hdr = req("GET", "/")
check("login page loads over TLS", st == 200)
check("HSTS header present", "Strict-Transport-Security" in hdr)
check("CSP header present", "frame-ancestors 'none'" in hdr.get("Content-Security-Policy", ""))
check("no-store on responses", hdr.get("Cache-Control") == "no-store")

print("authentication")
st, j, _ = req("GET", "/api/list?kind=claim")
check("records need a login (401)", st == 401, st)
st, j, _ = req("GET", "/api/list?kind=claim", token="made-up-token")
check("a made-up token is refused", st == 401, st)
st, j, _ = req("POST", "/api/login", {"user": "blayne", "password": "wrong password here"})
check("wrong password refused", st == 401 and "Wrong" in j.get("error", ""), (st, j))
st, j2, _ = req("POST", "/api/login", {"user": "nobody", "password": "wrong password here"})
check("unknown user gets the same message", st == 401 and j2.get("error") == j.get("error"))
st, j, _ = req("POST", "/api/login", {"user": "blayne", "password": PW})
check("right password logs in", st == 200 and j.get("token"), (st, j))
TOK = j.get("token")
st, j, _ = req("GET", "/api/whoami", token=TOK)
check("whoami names the person", j.get("user") == "blayne", j)
st, j, _ = req("POST", "/api/save", {"kind": "patient", "data": {"last_name": "Test", "first_name": "Patient", "dob": "01/01/1980"}}, token=TOK)
check("a logged-in save works", st == 200 and j.get("id"), (st, j))
PID = j.get("id")
st, j, _ = req("GET", f"/api/rec/{PID}", token=TOK)
check("a logged-in read works", st == 200 and j["data"].get("patient_name") == "TEST, PATIENT", j)

print("lockout")
for _ in range(cw.MAX_FAILURES):
    req("POST", "/api/login", {"user": "dad", "password": "not the password"})
st, j, _ = req("POST", "/api/login", {"user": "dad", "password": "another long passphrase 9"})
check("the right password is refused while locked out", st == 429, (st, j))
cw.SESSIONS.fails.clear()

print("sessions")
st, j, _ = req("POST", "/api/login", {"user": "dad", "password": "another long passphrase 9"})
DAD = j.get("token")
check("second person logs in separately", st == 200 and DAD and DAD != TOK)
cw.SESSIONS.live[DAD]["last"] -= cw.IDLE_SECONDS + 1
st, _, _ = req("GET", "/api/whoami", token=DAD)
check("session expires after the idle limit", st == 401, st)
st, j, _ = req("POST", "/api/login", {"user": "dad", "password": "another long passphrase 9"})
DAD = j.get("token")
users = cw.load_users(); users["dad"]["disabled"] = True; cw.save_users(users)
st, _, _ = req("GET", "/api/whoami", token=DAD)
check("disabling a user ends their live session", st == 401, st)
st, _, _ = req("POST", "/api/login", {"user": "dad", "password": "another long passphrase 9"})
check("a disabled user cannot log in", st == 401, st)
req("POST", "/api/logout", {}, token=TOK)
st, _, _ = req("GET", "/api/whoami", token=TOK)
check("a token is dead after logout", st == 401, st)

print("audit")
acc = [json.loads(x) for x in (Path(os.environ["THUNDER_VAULT"]) / "access.log").read_text().splitlines()]
check("access log records who", any(a["who"] == "blayne" and a["path"].startswith("/api/rec/") for a in acc))
check("access log records refused requests", any(a["who"] == "anonymous" and a["status"] == 401 for a in acc))
check("access log carries no patient name", "TEST" not in json.dumps(acc).upper().replace("/API/", ""))
aud = [json.loads(x) for x in (Path(os.environ["THUNDER_VAULT"]) / "audit.log").read_text().splitlines()]
check("vault audit credits the logged-in person, not the Unix account",
      any(a["who"] == "blayne" and a["record"] == PID for a in aud), aud[-3:])

print("network guard")
r = subprocess.run([sys.executable, str(Path(__file__).parent / "claims_web.py"), "--host", "0.0.0.0", "--port", "1"],
                   capture_output=True, text=True, env=os.environ, timeout=30)
check("refuses to listen on the network without TLS", r.returncode == 2 and "TLS" in r.stdout, r.stdout)

srv.shutdown()
print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
