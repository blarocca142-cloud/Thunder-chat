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
       "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    # keyUsage matters: Python 3.13+ verifies with VERIFY_X509_STRICT, which
    # rejects a CA certificate without it (Main runs 3.14).


d = TMP / "tls"; d.mkdir()
make_ca(d, "Test Fleet CA")
sh("openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", str(d / "server.key"),
   "-out", str(d / "server.csr"), "-subj", "/CN=localhost")
(d / "ext.cnf").write_text("subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=CA:FALSE\n"
                          "keyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n")
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

print("payments")
st, j, _ = req("POST", "/api/login", {"user": "blayne", "password": PW})
TOK = j.get("token")
st, j, _ = req("POST", "/api/save", {"kind": "claim", "data": {"patient_name": "TEST, PATIENT", "insurer": "Test Mutual",
    "date_of_service": "01/02/2026", "procedures": [{"code": "98941", "units": "1", "charge": "100"}, {"code": "97140", "units": "2", "charge": "25"}],
    "tracking": {"billing": "sent"}}}, token=TOK)
CID = j.get("id")
st, j, _ = req("GET", "/api/open_lines?source=payer&payer=test%20mutual", token=TOK)
check("open lines are found for the payer (case-insensitive)", st == 200 and len([l for l in j["lines"] if l["claim_id"] == CID]) == 2, j)
st, j, _ = req("POST", "/api/save", {"kind": "payment", "data": {"source": "payer", "payer": "Test Mutual", "amount": "90", "date": "02/01/2026",
    "method": "CHECK", "lines": [{"claim_id": CID, "line": 0, "paid": "80", "adjustments": [{"amt": "20", "group": "CO", "reason": "45"}]},
                                 {"claim_id": CID, "line": 1, "paid": "10"}]}}, token=TOK)
PAYID = j.get("id")
check("a payment posts", st == 200 and PAYID and j.get("remaining") == 0, j)
st, j, _ = req("GET", f"/api/rec/{CID}", token=TOK)
check("claim ledger shows paid and adjusted", j.get("ledger", {}).get("paid") == 90 and j["ledger"]["adj"] == 20, j.get("ledger"))
check("claim moves to Partly Paid on its own", j["data"]["tracking"]["billing"] == "partial", j["data"]["tracking"])
check("the payment is noted on the claim", any("Test Mutual" in n["note"] for n in j["data"]["notes_log"]))
st, j, _ = req("POST", "/api/save", {"kind": "payment", "id": PAYID, "data": {"source": "payer", "payer": "Test Mutual", "amount": "130",
    "date": "02/01/2026", "method": "CHECK", "lines": [{"claim_id": CID, "line": 0, "paid": "80", "adjustments": [{"amt": "20", "group": "CO", "reason": "45"}]},
                                                       {"claim_id": CID, "line": 1, "paid": "50"}]}}, token=TOK)
st, j, _ = req("GET", f"/api/rec/{CID}", token=TOK)
check("paying the rest moves it to Paid", j["data"]["tracking"]["billing"] == "paid", j["data"]["tracking"])
claims = req("GET", "/api/list?kind=claim", token=TOK)[1]["records"]
check("claim list balance comes from payments", [c for c in claims if c["id"] == CID][0]["balance"] == 0)
st, j, _ = req("POST", "/api/save", {"kind": "payment", "data": {"source": "payer", "payer": "X", "amount": "5", "date": "02/01/2026",
    "lines": [{"claim_id": "c-does-not-exist", "line": 0, "paid": "5"}]}}, token=TOK)
check("a payment against a missing claim is refused", st == 400, (st, j))
st, j, _ = req("POST", "/api/save", {"kind": "payment", "data": {"source": "payer", "payer": "X", "amount": "5", "date": "02/01/2026",
    "lines": [{"claim_id": CID, "line": 9, "paid": "5"}]}}, token=TOK)
check("a payment against a missing service line is refused", st == 400, (st, j))
st, _, _ = req("GET", "/api/open_lines?source=payer&payer=x")
check("open lines need a login", st == 401)

print("statements")
st, j, _ = req("POST", "/api/save", {"kind": "patient", "data": {"last_name": "Statement", "first_name": "Sam", "dob": "02/02/1970",
    "address": "1 Test Way", "city": "Anytown", "state": "NY", "zip": "12345", "insurer": "Test Mutual"}}, token=TOK)
SPID = j.get("id")
st, j, _ = req("POST", "/api/save", {"kind": "claim", "data": {"patient_id": SPID, "patient_name": "STATEMENT, SAM", "insurer": "Test Mutual",
    "date_of_service": "01/05/2026", "procedures": [{"code": "98941", "units": "1", "charge": "100"}, {"code": "97140", "units": "1", "charge": "40", "resp": "pat"}],
    "tracking": {"billing": "sent"}}}, token=TOK)
SCID = j.get("id")
st, j, _ = req("POST", "/api/save", {"kind": "payment", "data": {"source": "payer", "payer": "Test Mutual", "amount": "60", "date": "02/01/2026",
    "lines": [{"claim_id": SCID, "line": 0, "paid": "60", "adjustments": [{"amt": "25", "group": "CO", "reason": "45"}, {"amt": "15", "group": "PR", "reason": "2"}]}]}}, token=TOK)
st, j, _ = req("GET", f"/api/rec/{SCID}", token=TOK)
check("PR adjustments are not written off (balance stays open)", j["ledger"]["adj"] == 25 and j["ledger"]["pr"] == 15, j.get("ledger"))
rows = req("GET", "/api/statements?min=0.01&cycle=30", token=TOK)[1]["rows"]
mine = [r for r in rows if r["id"] == SPID]
check("statement list: PR coinsurance + a patient-responsible line = patient balance", mine and mine[0]["pat_bal"] == 55 and mine[0]["ins_bal"] == 0, mine)
st, j, _ = req("GET", f"/api/statement/{SPID}", token=TOK)
check("statement detail: Please Pay matches and aging adds up", j.get("please_pay") == 55 and round(sum(j["aging"].values()), 2) == 55, j.get("aging"))
st, j, _ = req("POST", "/api/statements/printed", {"items": [{"id": SPID, "pat_msg": "Thanks", "amount": 55}], "date": "03/01/2026"}, token=TOK)
check("confirming a good print records the statement", j.get("updated") == 1)
from datetime import date
rows = req("GET", "/api/statements?min=0.01&cycle=100000", token=TOK)[1]["rows"]
check("a patient billed within the cycle is left off the list", not [r for r in rows if r["id"] == SPID])
rows = req("GET", "/api/statements?min=0.01&cycle=0", token=TOK)[1]["rows"]
check("cycle 0 brings them back, with the date and message", [r for r in rows if r["id"] == SPID and r["last_statement_date"] == "03/01/2026" and r["pat_msg"] == "Thanks"])
st, _, _ = req("GET", "/api/statements")
check("statements need a login", st == 401)

print("florida pip")
row = [r for r in req("GET", "/api/list?kind=claim", token=TOK)[1]["records"] if r["id"] == SCID]
check("claims list carries the PIP clock", row and "pip_text" in row[0] and "pip_level" in row[0], row)
st, j, _ = req("GET", f"/api/rec/{SCID}", token=TOK)
check("an open claim carries its PIP check (a missing date of injury is flagged)", j.get("pip", {}).get("applies") is True
      and any(f["key"] == "no_doi" for f in j["pip"]["flags"]), j.get("pip"))
st, j, _ = req("GET", f"/api/rec/{SPID}", token=TOK)
check("a patient carries PIP benefits: the carrier's $60 counts toward the limit", j.get("benefits", {}).get("paid_ours") == 60, j.get("benefits"))
st, j, _ = req("POST", "/api/benefits", {"id": SPID, "data": {**req("GET", f"/api/rec/{SPID}", token=TOK)[1]["data"], "emc": "no"}}, token=TOK)
check("unsaved EMC edits are priced live", j.get("limit") == 2500 and j.get("remaining") == 2440, j)
st, _, _ = req("POST", "/api/benefits", {"id": SPID, "data": {}})
check("benefits need a login", st == 401)
st, _, _ = req("POST", "/api/benefits", {"id": "../x", "data": {}}, token=TOK)
check("benefits refuse a bad id", st == 400)
st, j, _ = req("POST", "/api/save", {"kind": "claim", "data": {"patient_name": "DENIED, TEST", "date_of_injury": "01/01/2026", "accident_state": "FL",
    "procedures": [{"code": "98941", "date": "01/05/2026", "charge": "100"}],
    "tracking": {"billing": "denied", "sent_date": "01/20/2026", "denial_code": "ime", "demand_sent": "03/01/2026", "demand_received": "03/05/2026"}}}, token=TOK)
p = req("GET", f"/api/rec/{j.get('id')}", token=TOK)[1].get("pip", {})
check("a saved denial keeps its type, and the demand clock runs from the green card",
      any(f["key"] == "denial" for f in p.get("flags", [])) and any(i["key"] == "demand" and i["date"] == "04/04/2026" for i in p.get("items", [])), p)
row = [r for r in req("GET", "/api/list?kind=patient", token=TOK)[1]["records"] if r["id"] == SPID]
check("patients list carries PIP left", row and "pip_left" in row[0], row)

print("network guard")
r = subprocess.run([sys.executable, str(Path(__file__).parent / "claims_web.py"), "--host", "0.0.0.0", "--port", "1"],
                   capture_output=True, text=True, env=os.environ, timeout=30)
check("refuses to listen on the network without TLS", r.returncode == 2 and "TLS" in r.stdout, r.stdout)

srv.shutdown()
print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
