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

    ./claims_web.py                     # this machine only, http://127.0.0.1:8770
    THUNDER_CLAIMS_PASSWORD=... ./claims_web.py --host 10.168.168.10

Standard library only, so it runs wherever the vault does. Binding anywhere but
loopback requires a password (HTTP basic auth): these are patient records, and
an open page on the LAN is the thing the vault exists to prevent.

Synthetic patients only until Blayne says otherwise.
"""
from __future__ import annotations

import argparse
import base64
import hmac
import json
import os
import re
import secrets
import sys
import tempfile
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


class Handler(BaseHTTPRequestHandler):
    password: str | None = None
    server_version = "ThunderClaims/2"

    def log_message(self, fmt, *args):  # no request lines on stdout
        pass

    user = "blayne"

    def _authed(self) -> bool:
        if not self.password:
            return True
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                name, pw = base64.b64decode(h[6:]).decode().split(":", 1)
                if hmac.compare_digest(pw, self.password):
                    self.user = (re.sub(r"[^A-Za-z0-9_.-]", "", name) or "user")[:32]
                    return True
            except Exception:
                pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Thunder Claims"')
        self.end_headers()
        return False

    def _send(self, code: int, body, ctype="application/json"):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD:
            raise ValueError("file too large (25 MB max)")
        return self.rfile.read(n)

    def _err(self, e: BaseException):
        self._send(500, {"error": str(e).splitlines()[0] if str(e) else type(e).__name__})

    def do_GET(self):
        if not self._authed():
            return
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html"):
                return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if u.path == "/api/whoami":
                return self._send(200, {"user": self.user})
            if u.path == "/api/list":
                kind = (parse_qs(u.query).get("kind") or ["claim"])[0]
                if kind not in KINDS:
                    return self._send(400, {"error": "unknown record type"})
                return self._send(200, {"records": list_records(kind)})
            if u.path == "/api/claims":  # kept for older pages
                return self._send(200, {"claims": list_records("claim")})
            m = re.match(r"^/api/(?:rec|claims)/([A-Za-z0-9_-]+)$", u.path)
            if m:
                rid = m.group(1)
                r = vault.get(rid)
                kind = kind_of(rid)
                body = {"id": rid, "kind": kind, "data": r, "claim": r}
                if kind == "claim":
                    body.update(assess(r))
                return self._send(200, body)
            self._send(404, {"error": "not found"})
        except BaseException as e:
            self._err(e)

    def do_POST(self):
        if not self._authed():
            return
        path = urlparse(self.path).path
        try:
            if path == "/api/check":
                return self._send(200, assess(json.loads(self._body() or b"{}")))
            if path == "/api/save":
                b = json.loads(self._body() or b"{}")
                return self._send(200, save(b.get("kind") or "", b.get("id"), b.get("data") or {}, self.user))
            if path == "/api/claims":  # kept for older pages
                b = json.loads(self._body() or b"{}")
                return self._send(200, save("claim", b.get("id"), b.get("claim") or {}, self.user))
            if path == "/api/scan":
                return self._send(200, scan(self._body(), self.headers.get("X-Filename", "")))
            self._send(404, {"error": "not found"})
        except ValueError as e:
            self._send(400, {"error": str(e)})
        except BaseException as e:
            self._err(e)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8770)
    a = ap.parse_args()
    pw = os.environ.get("THUNDER_CLAIMS_PASSWORD") or None
    if a.host not in ("127.0.0.1", "localhost", "::1") and not pw:
        print("Refusing to open patient records to the network without a password.\n"
              "Set THUNDER_CLAIMS_PASSWORD, or leave --host at 127.0.0.1.")
        return 2
    try:
        vault.keys_load()
    except SystemExit as e:
        print(f"Vault not ready: {e}")
        return 2
    Handler.password = pw
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"Thunder Claims on http://{a.host}:{a.port}/"
          + ("  (password required)" if pw else ""))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
