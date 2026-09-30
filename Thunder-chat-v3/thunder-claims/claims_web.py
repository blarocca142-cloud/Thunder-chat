#!/usr/bin/env python3
"""Thunder Claims - the claim screen, in a browser.

The pieces already worked from the command line: OCR, extraction, repair,
validation, the encrypted vault. Nobody bills from a command line, so this
puts one screen in front of them: a list of claims, a claim form laid out like
the paper one, the checks running as you type, and Save going straight into
the vault. Nothing is ever submitted to a payer from here.

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
from urllib.parse import urlparse

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import intake  # noqa: E402  (brings vault, extract, repair, validate, codelist)
from intake import codelist, vault  # noqa: E402

PAGE = HERE / "claims_web.html"
INDEX_FIELDS = ["patient_name", "claim_number"]
MAX_UPLOAD = 25 * 1024 * 1024
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


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


def list_claims() -> list[dict]:
    """Every record, newest first. Each one is decrypted (and audited) to show
    its name - that is the cost of a list a person can actually read."""
    out = []
    for p in sorted(vault.records_dir().glob("*.rec"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            c = vault.get(p.stem)
        except BaseException as e:  # vault raises SystemExit on a bad record
            out.append({"id": p.stem, "error": str(e).splitlines()[0]})
            continue
        meta = c.get("_meta") or {}
        out.append({
            "id": p.stem,
            "patient_name": c.get("patient_name", ""),
            "date_of_service": c.get("date_of_service", ""),
            "insurer": c.get("insurer", ""),
            "status": meta.get("status", ""),
            "saved": meta.get("saved", ""),
        })
    return out


def save_claim(record_id: str | None, claim: dict) -> dict:
    claim = {k: v for k, v in claim.items() if k != "_meta"}
    a = assess(claim)
    rid = record_id or time.strftime("c%Y%m%d-%H%M%S-") + secrets.token_hex(2)
    if not ID_RE.match(rid):
        raise ValueError("bad record id")
    claim["_meta"] = {"status": a["status"], "reasons": a["reasons"],
                      "saved": time.strftime("%Y-%m-%d %H:%M")}
    vault.put(rid, claim, INDEX_FIELDS)
    return {"id": rid, **a}


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
    server_version = "ThunderClaims/1"

    def log_message(self, fmt, *args):  # no request lines on stdout
        pass

    def _authed(self) -> bool:
        if not self.password:
            return True
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                _, pw = base64.b64decode(h[6:]).decode().split(":", 1)
                if hmac.compare_digest(pw, self.password):
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

    def do_GET(self):
        if not self._authed():
            return
        path = urlparse(self.path).path
        try:
            if path in ("/", "/index.html"):
                return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if path == "/api/claims":
                return self._send(200, {"claims": list_claims()})
            m = re.match(r"^/api/claims/([A-Za-z0-9_-]+)$", path)
            if m:
                c = vault.get(m.group(1))
                return self._send(200, {"id": m.group(1), "claim": c, **assess(c)})
            self._send(404, {"error": "not found"})
        except BaseException as e:
            self._send(500, {"error": str(e).splitlines()[0] if str(e) else type(e).__name__})

    def do_POST(self):
        if not self._authed():
            return
        path = urlparse(self.path).path
        try:
            if path == "/api/check":
                return self._send(200, assess(json.loads(self._body() or b"{}")))
            if path == "/api/claims":
                b = json.loads(self._body() or b"{}")
                return self._send(200, save_claim(b.get("id"), b.get("claim") or {}))
            if path == "/api/scan":
                return self._send(200, scan(self._body(), self.headers.get("X-Filename", "")))
            self._send(404, {"error": "not found"})
        except ValueError as e:
            self._send(400, {"error": str(e)})
        except BaseException as e:
            self._send(500, {"error": str(e).splitlines()[0] if str(e) else type(e).__name__})


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
