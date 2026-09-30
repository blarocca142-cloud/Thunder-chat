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
import fl_pip  # noqa: E402
import reports  # noqa: E402
import validate  # noqa: E402

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
    "payment":  {"prefix": "pay-", "index": []},
    "procedure": {"prefix": "px-", "index": []},
    "template": {"prefix": "tpl-", "index": []},
    "task":     {"prefix": "tk-", "index": []},
}
BILLING = ("draft", "sent", "hold", "paid", "partial", "denied")
METHODS = ("CHECK", "EFT", "CASH", "CREDIT CARD", "MONEY ORDER", "OTHER")
FIRST_ACCOUNT = 1000  # EZClaim numbers patients from 1000 up


def kind_of(record_id: str) -> str:
    for k in ("patient", "payer", "provider", "payment", "procedure", "template", "task"):
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
    return {"status": status, "reasons": reasons, "issues": issues, "codes": codes,
            "pip": fl_pip.deadlines(claim)}


def records(kind: str):
    """(id, record) for every readable record of one kind, newest first."""
    for p in sorted(vault.records_dir().glob("*.rec"), key=lambda p: p.stat().st_mtime, reverse=True):
        if kind_of(p.stem) == kind:
            try:
                yield p.stem, vault.get(p.stem)
            except BaseException:
                continue


def ledger(exclude: str | None = None) -> dict:
    """What posted payments have done to each claim and service line:
    {claim_id: {"paid", "adj", "pr", "pat_paid", "lines": {idx: {... "entries"}}}}.

    adj  = write-offs (group codes CO, OA, PI, CR) - they close the balance.
    pr   = patient responsibility (group PR: deductible, coinsurance, copay).
           It does NOT close the balance; it moves that part to the patient,
           which is what a statement then bills.
    Balances are always computed from the payments, never stored, so they
    cannot drift from what was actually posted."""
    out: dict = {}
    zero = lambda: {"paid": 0.0, "adj": 0.0, "pr": 0.0, "pat_paid": 0.0}
    for pid, pay in records("payment"):
        if pid == exclude:
            continue
        from_patient = pay.get("source") == "patient"
        who = (pay.get("patient_name") or "Patient") if from_patient else pay.get("payer")
        for a in pay.get("lines") or []:
            cid, li = a.get("claim_id"), int(a.get("line") or 0)
            paid = money(a.get("paid"))
            adjs = a.get("adjustments") or []
            pr = sum(money(x.get("amt")) for x in adjs if str(x.get("group") or "").upper() == "PR")
            adj = sum(money(x.get("amt")) for x in adjs if str(x.get("group") or "").upper() != "PR")
            c = out.setdefault(cid, {**zero(), "lines": {}})
            line = c["lines"].setdefault(li, {**zero(), "entries": []})
            for t in (c, line):
                t["paid"] += paid; t["adj"] += adj; t["pr"] += pr
                if from_patient:
                    t["pat_paid"] += paid
            line["entries"].append({"payment": pid, "date": pay.get("date", ""), "from": who or "", "source": pay.get("source", ""),
                                    "paid": paid, "adj": adj, "pr": pr,
                                    "codes": ", ".join(f"{x.get('group', '')}-{x.get('reason', '')}".strip("-")
                                                       for x in adjs if money(x.get("amt")))})
    for c in out.values():
        for k in ("paid", "adj", "pr", "pat_paid"):
            c[k] = round(c[k], 2)
            for line in c["lines"].values():
                line[k] = round(line[k], 2)
    return out


def claim_lines(cid: str, c: dict, led: dict) -> list[dict]:
    """Per service line: charge, paid, adjusted, balance, and how that balance
    splits between the patient and the insurance. A line marked Resp. = Pat
    (or a claim with no insurer) is all patient; otherwise the patient owes the
    PR amounts the payer assigned, less what the patient has paid."""
    posted = (led.get(cid) or {}).get("lines") or {}
    manual = money((c.get("tracking") or {}).get("paid_amount"))  # pre-Payment-Entry "amount paid" box
    out = []
    for i, p in enumerate(c.get("procedures") or []):
        if not str((p or {}).get("code") or "").strip():
            continue
        l = posted.get(i) or {"paid": 0.0, "adj": 0.0, "pr": 0.0, "pat_paid": 0.0, "entries": []}
        charge = line_charge(p)
        take = min(max(manual, 0), max(charge - l["paid"] - l["adj"], 0))
        manual -= take
        bal = round(charge - l["paid"] - l["adj"] - take, 2)
        resp = (p.get("resp") or ("ins" if str(c.get("insurer") or "").strip() else "pat")).lower()
        pat = bal if resp == "pat" else round(l["pr"] - l["pat_paid"], 2)
        pat = bal if bal < 0 else min(pat, bal)          # a credit belongs to the patient
        out.append({"line": i, "date": p.get("date") or c.get("date_of_service", ""), "code": p.get("code", ""),
                    "description": p.get("description", ""), "charge": charge, "paid": round(l["paid"] + take, 2),
                    "adj": l["adj"], "pr": l["pr"], "balance": bal, "pat_bal": round(pat, 2), "ins_bal": round(bal - pat, 2),
                    "resp": resp, "entries": l["entries"]})
    return out


def line_charge(p: dict) -> float:
    return round((money((p or {}).get("units")) or 1) * money((p or {}).get("charge")), 2)


def summary(kind: str, rid: str, r: dict, led: dict | None = None, claims: list | None = None) -> dict:
    if kind == "payment":
        applied = round(sum(money(a.get("paid")) for a in r.get("lines") or []), 2)
        amount = money(r.get("amount"))
        return {"id": rid, "date": r.get("date", ""), "source": r.get("source", ""), "payer": r.get("payer", ""),
                "patient_name": r.get("patient_name", ""), "amount": amount, "applied": applied,
                "remaining": round(amount - applied, 2), "method": r.get("method", ""), "ref": r.get("ref", "")}
    if kind == "claim":
        meta = r.get("_meta") or {}
        track = r.get("tracking") or {}
        charges = total_charges(r)
        posted = (led or {}).get(rid) or {"paid": 0.0, "adj": 0.0}
        lines = claim_lines(rid, r, led or {})
        pip = fl_pip.deadlines(r)
        paid = round(money(track.get("paid_amount")) + posted["paid"], 2)
        return {"id": rid, "patient_name": r.get("patient_name", ""),
                "account_number": r.get("account_number", ""),
                "patient_id": r.get("patient_id", ""),
                "date_of_service": r.get("date_of_service", ""),
                "insurer": r.get("insurer", ""), "status": meta.get("status", ""),
                "billing": track.get("billing") or "draft",
                "charges": charges, "paid": paid, "adjusted": posted["adj"],
                "balance": round(charges - paid - posted["adj"], 2),
                "pat_bal": round(sum(x["pat_bal"] for x in lines), 2), "ins_bal": round(sum(x["ins_bal"] for x in lines), 2),
                "pip_level": pip["level"], "pip_text": pip["text"], "method": track.get("method") or "paper",
                "sent_date": track.get("sent_date", ""), "claim_number": r.get("claim_number", ""),
                "treating_provider": r.get("treating_provider", ""), "last_printed": track.get("last_printed", ""),
                "clinic_name": r.get("clinic_name", ""),
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
                "reminder": r.get("reminder", ""),
                **({"pip_left": b["remaining"], "pip_limit": b["limit"], "pip_level": b["level"]}
                   if claims is not None and (b := patient_benefits(rid, r, claims, led)) else {})}
    if kind == "template":
        return {"id": rid, "name": r.get("name", ""), "lines": len(r.get("procedures") or []),
                "codes": " ".join(str(p.get("code") or "") for p in r.get("procedures") or [])}
    if kind == "task":
        return {"id": rid, "subject": r.get("subject", ""), "due": r.get("due", ""), "assigned": r.get("assigned", ""),
                "done": bool(r.get("done")) or r.get("status") == "Completed", "status": r.get("status") or "Not Started",
                "priority": r.get("priority", "Normal"), "about": r.get("about", ""),
                "about_id": r.get("about_id", ""), "created_by": r.get("created_by", "")}
    if kind == "procedure":
        return {"id": rid, "code": r.get("code", ""), "modifier": r.get("modifier", ""), "description": r.get("description", ""),
                "charge": money(r.get("charge")), "units": r.get("units", ""), "pointer": r.get("pointer", ""),
                "active": r.get("active", True) is not False}
    if kind == "payer":
        return {"id": rid, "name": r.get("name", ""), "payer_id": r.get("payer_id", ""),
                "phone": r.get("phone", "")}
    return {"id": rid, "name": r.get("name", ""), "npi": r.get("npi", ""),
            "role": r.get("role", ""), "tax_id": r.get("tax_id", "")}


def list_records(kind: str) -> list[dict]:
    """Every record of one kind, newest first. Each one is decrypted (and
    audited) to show its name - the cost of a list a person can read."""
    out = []
    led = ledger() if kind in ("claim", "patient") else None
    claims = list(records("claim")) if kind == "patient" else None
    for p in sorted(vault.records_dir().glob("*.rec"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        if kind_of(p.stem) != kind:
            continue
        try:
            r = vault.get(p.stem)
        except BaseException as e:  # vault raises SystemExit on a bad record
            out.append({"id": p.stem, "error": str(e).splitlines()[0]})
            continue
        out.append(summary(kind, p.stem, r, led, claims))
    return out


def open_lines(source: str, payer: str, patient_id: str, patient_name: str,
               ignore_rp: bool, include_zero: bool, payment_id: str | None) -> list[dict]:
    """Service lines a payment can be applied to - EZClaim's Payment Entry grid.
    Balances leave out the payment being edited, so its own amounts are not
    counted twice."""
    led = ledger(exclude=payment_id)
    mine = set()
    if payment_id:
        try:
            mine = {(a.get("claim_id"), int(a.get("line") or 0)) for a in vault.get(payment_id).get("lines") or []}
        except BaseException:
            mine = set()
    norm = lambda x: str(x or "").strip().upper()
    out = []
    for cid, c in records("claim"):
        if source == "payer" and not ignore_rp and norm(c.get("insurer")) != norm(payer):
            if not any(m[0] == cid for m in mine):
                continue
        if source == "patient" and not ignore_rp:
            same = c.get("patient_id") == patient_id if c.get("patient_id") and patient_id else norm(c.get("patient_name")) == norm(patient_name)
            if not same and not any(m[0] == cid for m in mine):
                continue
        manual = money((c.get("tracking") or {}).get("paid_amount"))  # pre-Payment-Entry "amount paid" box
        for i, p in enumerate(c.get("procedures") or []):
            if not str((p or {}).get("code") or "").strip():
                continue
            charge = line_charge(p)
            l = ((led.get(cid) or {}).get("lines") or {}).get(i) or {"paid": 0.0, "adj": 0.0}
            take = min(max(manual, 0), max(charge - l["paid"] - l["adj"], 0))
            manual -= take
            applied = round(l["paid"] + l["adj"] + take, 2)
            bal = round(charge - applied, 2)
            if abs(bal) < 0.005 and not include_zero and (cid, i) not in mine:
                continue
            out.append({"claim_id": cid, "line": i, "patient_name": c.get("patient_name", ""),
                        "dos": p.get("date") or c.get("date_of_service", ""), "proc": p.get("code", ""),
                        "mod": p.get("modifier", ""), "charge": charge, "payer": c.get("insurer", ""),
                        "applied": applied, "balance": bal})
    out.sort(key=lambda x: (x["patient_name"], x["dos"], x["claim_id"], x["line"]))
    return out


# --------------------------------------------------------------------------
# patient statements (EZClaim's Statements screen)
# --------------------------------------------------------------------------

SETTINGS_FILE = Path(os.environ.get("THUNDER_CLAIMS_SETTINGS",
                                    str(Path.home() / ".thunder" / "claims_settings.json")))
STATEMENT_DEFAULTS = {"return_name": "", "return_addr1": "", "return_addr2": "", "return_city": "", "return_state": "",
                      "return_zip": "", "return_phone": "", "days_history": 30, "hide_aging": False,
                      "hide_proc": False, "global_message": "", "messages": []}


SETUP_DEFAULTS = {
    # General
    "alt_rows": False,
    # Patient
    "auto_account": True, "next_account": "", "account_prefix": "", "unique_account": True, "accept_assignment": "Yes",
    # Claim
    "initial_status": "draft", "initial_pos": "11", "initial_state": "FL", "initial_insurance_type": "other",
    "default_billing": "", "default_rendering": "", "default_referring": "",
}


def settings_file() -> Path:
    """Each company file has its own options, as in EZClaim. The first
    company keeps the original settings file so nothing moves on upgrade."""
    c = current_company()
    return SETTINGS_FILE if not c or c.get("default") else Path(c["path"]) / "settings.json"


def get_settings() -> dict:
    """Practice-wide options (return address and the like) - no patient data."""
    try:
        s_ = json.loads(settings_file().read_text())
    except (FileNotFoundError, ValueError):
        s_ = {}
    return {"statement": {**STATEMENT_DEFAULTS, **(s_.get("statement") or {})},
            "setup": {**SETUP_DEFAULTS, **(s_.get("setup") or {})}}


def set_settings(body: dict) -> dict:
    allset = get_settings()
    cur, setup = allset["statement"], allset["setup"]
    for k, v in ((body or {}).get("setup") or {}).items():
        if k not in SETUP_DEFAULTS:
            continue
        if isinstance(SETUP_DEFAULTS[k], bool):
            setup[k] = bool(v)
        elif k == "initial_status":
            setup[k] = v if v in ("draft", "hold") else "draft"
        elif k == "next_account":
            setup[k] = str(int(money(v))) if money(v) else ""
        else:
            setup[k] = str(v or "")[:80]
    src = (body or {}).get("statement") or {}
    for k in ("return_name", "return_addr1", "return_addr2", "return_city", "return_state", "return_zip", "return_phone", "global_message"):
        if k in src:
            cur[k] = str(src[k] or "")[:120]
    if "days_history" in src:
        cur["days_history"] = max(0, min(3650, int(money(src["days_history"]))))
    for k in ("hide_aging", "hide_proc"):
        if k in src:
            cur[k] = bool(src[k])
    msg = cur["global_message"].strip()
    if msg and msg not in cur["messages"]:  # the message list grows as messages are used, as in EZClaim
        cur["messages"] = ([msg] + cur["messages"])[:30]
    sf = settings_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    tmp = sf.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"statement": cur, "setup": setup}, f, indent=2)
    os.replace(tmp, sf)
    return {"statement": cur, "setup": setup}


def _norm(x) -> str:
    return str(x or "").strip().upper()


def patient_claims(pid: str, p: dict, claims: list) -> list:
    return [(cid, c) for cid, c in claims
            if (c.get("patient_id") == pid) or (not c.get("patient_id") and _norm(c.get("patient_name")) == _norm(p.get("patient_name")))]


def patient_benefits(pid: str, p: dict, claims: list | None = None, led: dict | None = None) -> dict:
    """PIP limit used and left for one patient: what the carrier paid on this
    office's claims (patient payments excluded) plus what it paid others."""
    claims = list(records("claim")) if claims is None else claims
    led = ledger() if led is None else led
    paid = open_ins = 0.0
    for cid, c in patient_claims(pid, p, claims):
        posted = led.get(cid) or {"paid": 0.0, "pat_paid": 0.0}
        paid += posted["paid"] - posted.get("pat_paid", 0.0) + money((c.get("tracking") or {}).get("paid_amount"))
        open_ins += sum(max(x["ins_bal"], 0) for x in claim_lines(cid, c, led))
    return fl_pip.benefits(p, round(paid, 2), round(open_ins, 2))


def _days_since(d: str) -> int | None:
    from datetime import date
    x = validate.parse_date(str(d or ""))
    return (date.today() - x).days if x else None


def statement_list(min_bal: float, cycle: int, include_zero: bool) -> list[dict]:
    led = ledger()
    claims = list(records("claim"))
    out = []
    for pid, p in records("patient"):
        if p.get("active") is False or p.get("no_statements"):
            continue
        lines = [x for cid, c in patient_claims(pid, p, claims) for x in claim_lines(cid, c, led)]
        pat = round(sum(x["pat_bal"] for x in lines), 2)
        ins = round(sum(x["ins_bal"] for x in lines), 2)
        since = _days_since(p.get("last_statement_date"))
        if cycle > 0 and since is not None and since < cycle:
            continue
        if not (pat >= min_bal and (pat != 0 or include_zero)) and not (include_zero and pat == 0 and ins > 0):
            continue
        if not lines:
            continue
        out.append({"id": pid, "patient_name": p.get("patient_name", ""), "account_number": p.get("account_number", ""),
                    "pat_bal": pat, "ins_bal": ins, "pri_payer": p.get("insurer", ""),
                    "last_statement_date": p.get("last_statement_date", ""), "pat_msg": p.get("statement_msg", "")})
    out.sort(key=lambda r: r["patient_name"])
    return out


def statement_detail(pid: str) -> dict:
    """Everything one printed statement shows. Always current data - a reprint
    shows today's balances, not the original's (as in EZClaim)."""
    p = vault.get(pid)
    if kind_of(pid) != "patient":
        raise ValueError("not a patient")
    st = get_settings()["statement"]
    led = ledger()
    rows, aging = [], {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "91-120": 0.0, "Over 120": 0.0}
    for cid, c in patient_claims(pid, p, list(records("claim"))):
        for x in claim_lines(cid, c, led):
            age = _days_since(x["date"])
            recent = age is None or age <= st["days_history"]
            if abs(x["balance"]) < 0.005 and not recent:
                continue
            desc = x["description"] or ("Procedure " + x["code"])
            rows.append({"date": x["date"], "description": desc, "proc": x["code"], "amount": x["charge"],
                         "ins_bal": x["ins_bal"], "pat_bal": x["pat_bal"],
                         "note": "Patient responsibility" if x["pr"] > 0.004 or x["resp"] == "pat" else ""})
            for e in x["entries"]:
                if e["paid"]:
                    rows.append({"date": e["date"], "description": ("Payment - thank you" if e["source"] == "patient" else "Insurance payment - " + (e["from"] or "")),
                                 "proc": "", "amount": -e["paid"], "ins_bal": None, "pat_bal": None, "note": ""})
            b = "Over 120" if age is not None and age > 120 else "91-120" if age is not None and age > 90 else \
                "61-90" if age is not None and age > 60 else "31-60" if age is not None and age > 30 else "0-30"
            aging[b] += x["pat_bal"]
    rows.sort(key=lambda r: (validate.parse_date(str(r["date"] or "")) or validate.parse_date("01/01/1900"), r["amount"] < 0))
    pat_total = round(sum(aging.values()), 2)
    ins_total = round(sum(r["ins_bal"] for r in rows if r["ins_bal"] is not None), 2)
    return {"patient": {"id": pid, "name": p.get("patient_name", ""), "account_number": p.get("account_number", ""),
                        "address": p.get("address", ""), "address2": p.get("address2", ""), "city": p.get("city", ""),
                        "state": p.get("state", ""), "zip": p.get("zip", ""), "pat_msg": p.get("statement_msg", "")},
            "settings": st, "rows": rows, "aging": {k: round(v, 2) for k, v in aging.items()},
            "ins_bal": ins_total, "please_pay": pat_total}


def statements_printed(items: list, when: str, user: str) -> int:
    """Only runs after the person confirms the statements printed properly -
    that is what records Last Statement Date, as in EZClaim."""
    n = 0
    for it in items[:500]:
        pid = str((it or {}).get("id") or "")
        if not ID_RE.match(pid) or kind_of(pid) != "patient":
            continue
        p = vault.get(pid)
        p["last_statement_date"] = when
        if "pat_msg" in it:
            p["statement_msg"] = str(it.get("pat_msg") or "")[:200]
        p.setdefault("statements", []).append({"date": when, "amount": round(money(it.get("amount")), 2), "user": user})
        vault.put(pid, p, KINDS["patient"]["index"])
        n += 1
    return n


def clean_payment(data: dict) -> dict:
    src = data.get("source")
    if src not in ("payer", "patient"):
        raise ValueError("choose Payer or Patient as the payment source")
    if src == "payer" and not str(data.get("payer") or "").strip():
        raise ValueError("choose the payer")
    if src == "patient" and not str(data.get("patient_name") or "").strip():
        raise ValueError("choose the patient")
    if not str(data.get("date") or "").strip():
        raise ValueError("enter the payment date")
    if data.get("method") and data["method"] not in METHODS:
        raise ValueError("unknown payment method")
    data["amount"] = f"{money(data.get('amount')):.2f}"
    lines = []
    for a in data.get("lines") or []:
        cid = str(a.get("claim_id") or "")
        if not ID_RE.match(cid) or kind_of(cid) != "claim" or not vault.record_path(cid).exists():
            raise ValueError(f"unknown claim {cid!r}")
        li = int(a.get("line") or 0)
        if li < 0 or li >= len(vault.get(cid).get("procedures") or []):
            raise ValueError(f"claim {cid} has no service line {li + 1}")
        adjs = []
        for x in (a.get("adjustments") or [])[:4]:
            amt = money(x.get("amt"))
            if amt:
                adjs.append({"amt": f"{amt:.2f}", "group": str(x.get("group") or "")[:3].upper(),
                             "reason": str(x.get("reason") or "")[:10].upper(), "remark": str(x.get("remark") or "")[:10].upper()})
        paid = money(a.get("paid"))
        if paid or adjs:
            lines.append({"claim_id": cid, "line": li, "paid": f"{paid:.2f}", "adjustments": adjs})
    data["lines"] = lines
    return data


def after_payment(pid: str, pay: dict, touched: set, user: str) -> None:
    """Re-work the status of every claim the payment touches, and note it on
    the claim, as EZClaim does: fully paid -> Paid, partly -> Partly Paid."""
    led = ledger()
    who = pay.get("payer") if pay.get("source") == "payer" else (pay.get("patient_name") or "patient")
    for cid in sorted(touched):
        try:
            c = vault.get(cid)
        except BaseException:
            continue
        tr = c.setdefault("tracking", {})
        posted = led.get(cid) or {"paid": 0.0, "adj": 0.0}
        charges = total_charges(c)
        paid = money(tr.get("paid_amount")) + posted["paid"]
        bal = round(charges - paid - posted["adj"], 2)
        old = tr.get("billing") or "draft"
        if charges > 0 and bal <= 0.004:
            new = "paid"
        elif paid > 0.004 or posted["adj"] > 0.004:
            new = "partial" if old not in ("denied", "hold") else old
        else:
            new = "sent" if old in ("paid", "partial") else old
        tr["billing"] = new
        mine = [a for a in pay.get("lines") or [] if a.get("claim_id") == cid]
        p_amt = sum(money(a.get("paid")) for a in mine)
        a_amt = sum(money(x.get("amt")) for a in mine for x in a.get("adjustments") or [])
        text = (f"Payment {pay.get('date', '')} from {who}: paid ${p_amt:,.2f}, adjusted ${a_amt:,.2f}"
                if mine else f"Payment {pid} from {who} no longer applied to this claim")
        c.setdefault("notes_log", []).append(note(text, user, bal))
        vault.put(cid, c, KINDS["claim"]["index"])


def clean_procedure(data: dict, rid: str) -> dict:
    """A Procedure Code Library entry. One entry per code + modifier, as in
    EZClaim, so a code typed on a claim always finds exactly one."""
    code = str(data.get("code") or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{4,7}", code):
        raise ValueError("enter a procedure code (CPT/HCPCS, like 98941 or G0283)")
    mod = str(data.get("modifier") or "").strip().upper()[:2]
    for oid, o in records("procedure"):
        if oid != rid and str(o.get("code") or "").upper() == code and str(o.get("modifier") or "").upper() == mod:
            raise ValueError(f"{code}{'-' + mod if mod else ''} is already in the library")
    data.update(code=code, modifier=mod, description=str(data.get("description") or "").strip()[:80],
                charge=f"{money(data.get('charge')):.2f}", units=str(int(money(data.get("units")) or 1)),
                pointer=str(data.get("pointer") or "").strip()[:8], active=data.get("active", True) is not False)
    return data


def procedures_from_claims(user: str) -> dict:
    """Seed the library from what the office has actually billed: every code
    (+ modifier) on a claim that is not in the library yet, with its most
    recent charge and description. Nothing is invented."""
    have = {(str(o.get("code") or "").upper(), str(o.get("modifier") or "").upper()) for _, o in records("procedure")}
    seen: dict = {}
    for _, c in records("claim"):  # newest first, so the first charge seen is the latest
        for p in c.get("procedures") or []:
            code = str((p or {}).get("code") or "").strip().upper()
            key = (code, str(p.get("modifier") or "").strip().upper()[:2])
            if not re.fullmatch(r"[A-Z0-9]{4,7}", code) or key in have or key in seen:
                continue
            seen[key] = {"code": key[0], "modifier": key[1], "description": str(p.get("description") or "").strip(),
                         "charge": p.get("charge") or "0", "units": p.get("units") or "1", "added_from": "past claims"}
    for key, rec in sorted(seen.items()):
        save("procedure", None, rec, user)
    return {"added": len(seen)}


def print_check(cid: str, c: dict) -> list[dict]:
    """EZClaim's Errors and Warnings, for paper. An Error keeps the claim from
    printing; a Warning prints but will probably be denied. Messages are
    EZClaim's own wording where it has one. Like EZClaim's: this catches data
    entry mistakes, it does not check coding."""
    out = []

    def add(sev, msg):
        out.append({"severity": sev, "message": msg})

    procs = [p for p in c.get("procedures") or [] if str((p or {}).get("code") or "").strip()]
    if not str(c.get("patient_name") or "").strip():
        add("Error", "The patient's name is missing.")
    if not str(c.get("insurer") or "").strip():
        add("Error", "The payer is missing.")
    if not str(c.get("clinic_name") or "").strip():
        add("Error", "Billing Provider is missing.")
    if not procs:
        add("Error", "Procedure Code is missing.")
    if not any(str((d or {}).get("code") or "").strip() for d in c.get("diagnoses") or []):
        add("Error", "Needs DX")
    if not str(c.get("place_of_service") or "").strip():
        add("Error", "Place of Service is missing.")
    if any(not money((p or {}).get("charge")) for p in procs):
        add("Error", "A service line has no charge.")
    if not str(c.get("claim_number") or "").strip():
        add("Warning", "The Insured's ID # is missing.")
    if not str(c.get("dob") or "").strip():
        add("Warning", "The patient's date of birth is missing.")
    if not str(c.get("clinic_npi") or "").strip():
        add("Warning", "The billing NPI (33a) is missing.")
    elif not validate.npi_valid(str(c["clinic_npi"])):
        add("Warning", f"The billing NPI {c['clinic_npi']} fails the NPI check digit.")
    if not str(c.get("clinic_tax_id") or "").strip():
        add("Warning", "The billing Tax ID (25) is missing.")
    if not str(c.get("treating_npi") or "").strip():
        add("Warning", "The rendering provider NPI (24J) is missing.")
    if not str(c.get("insurer_address") or "").strip():
        add("Warning", "The payer's mailing address is missing - it prints in the window-envelope area.")
    codes = assess(c)["codes"]
    for code, ok in codes.items():
        if ok is False:
            add("Warning", f"{code} is not on the official code list.")
    pip = fl_pip.deadlines(c)
    for f in pip.get("flags") or []:
        if f["key"] in ("file_late", "billed_late", "initial", "dates"):
            add("Warning", "Florida PIP: " + f["text"])
    return out


def claims_printed(ids: list, when: str, user: str) -> int:
    """After "Did all the claims print properly?" - Yes. As in EZClaim, a
    printed Ready to Submit claim becomes Submitted with today's bill date."""
    n = 0
    for cid in ids:
        if not ID_RE.match(str(cid)) or kind_of(cid) != "claim" or not vault.record_path(cid).exists():
            continue
        c = vault.get(cid)
        tr = c.setdefault("tracking", {})
        tr["last_printed"] = when
        if (tr.get("billing") or "draft") == "draft":
            tr["billing"] = "sent"
            if not tr.get("sent_date"):
                tr["sent_date"] = when
        c.setdefault("notes_log", []).append(note(f"Printed on a CMS-1500 for mailing ({when})", user, total_charges(c)))
        vault.put(cid, c, KINDS["claim"]["index"])
        n += 1
    return n


def delete_record(rid: str, user: str) -> dict:
    """EZClaim's Delete, with the guards a billing office needs: a claim with
    money posted to it, or a patient with claims, cannot be deleted until
    those are dealt with. Deleting a payment re-works its claims' balances
    and statuses. Deleted records are kept, encrypted, under deleted/."""
    if not ID_RE.match(rid) or not vault.record_path(rid).exists():
        raise ValueError("no such record")
    kind = kind_of(rid)
    r = vault.get(rid)
    if kind == "claim":
        posted = ledger().get(rid)
        if posted and (posted["paid"] or posted["adj"] or posted["pr"]):
            raise ValueError("this claim has payments or adjustments posted - delete or change those payments first")
    if kind == "patient":
        linked = patient_claims(rid, r, list(records("claim")))
        if linked:
            raise ValueError(f"this patient has {len(linked)} claim(s) - delete or move those first")
    vault.retire(rid)
    if kind == "payment":
        touched = {a.get("claim_id") for a in r.get("lines") or [] if a.get("claim_id")}
        after_payment(rid, {**r, "lines": []}, {c for c in touched if vault.record_path(c).exists()}, user)
    return {"deleted": rid, "kind": kind}


def merge_patients(keep: str, drop: str, user: str) -> dict:
    """EZClaim's Merge Patient: every claim of the duplicate moves to the
    patient being kept, then the duplicate is deleted (recoverably)."""
    for x in (keep, drop):
        if not ID_RE.match(x) or kind_of(x) != "patient" or not vault.record_path(x).exists():
            raise ValueError("choose two saved patients")
    if keep == drop:
        raise ValueError("choose two different patients")
    k, dp = vault.get(keep), vault.get(drop)
    moved = 0
    for cid, c in patient_claims(drop, dp, list(records("claim"))):
        c.update(patient_id=keep, patient_name=k.get("patient_name", ""), account_number=k.get("account_number", ""))
        c.setdefault("notes_log", []).append(note(f"Moved here when patient {dp.get('account_number') or drop} was merged into {k.get('account_number') or keep}",
                                                  user, total_charges(c)))
        vault.put(cid, c, KINDS["claim"]["index"])
        moved += 1
    vault.retire(drop)
    return {"kept": keep, "moved": moved}


def write_off(cid: str, group: str, reason: str, user: str) -> dict:
    """EZClaim's Write Off Claim: an adjustment for whatever is still open on
    every line, posted as a $0.00 payment so it shows up - and can be undone -
    like any other."""
    if not ID_RE.match(cid) or kind_of(cid) != "claim" or not vault.record_path(cid).exists():
        raise ValueError("no such claim")
    c = vault.get(cid)
    lines = [{"claim_id": cid, "line": x["line"], "paid": "0",
              "adjustments": [{"amt": f"{x['balance']:.2f}", "group": (group or "CO")[:2].upper(), "reason": (reason or "45")[:5].upper()}]}
             for x in claim_lines(cid, c, ledger()) if x["balance"] > 0.004]
    if not lines:
        raise ValueError("nothing left to write off on this claim")
    pay = {"source": "payer", "payer": c.get("insurer") or "WRITE-OFF", "date": time.strftime("%m/%d/%Y"), "method": "OTHER",
           "ref": "WRITE-OFF", "amount": "0", "lines": lines, "note": "Write Off Claim"}
    return save("payment", None, pay, user)


def new_id(kind: str) -> str:
    return KINDS[kind]["prefix"] + time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2)


def next_account_number() -> str:
    """EZClaim's Program Setup > Patient: prefix + the Next Account Number,
    never lower than one more than the highest already on file."""
    su = get_settings()["setup"]
    pre = su.get("account_prefix") or ""
    top = FIRST_ACCOUNT - 1
    for p in list_records("patient"):
        a = str(p.get("account_number") or "").strip()
        if pre and a.startswith(pre):
            a = a[len(pre):]
        try:
            top = max(top, int(a))
        except ValueError:
            pass
    n = max(top + 1, int(money(su.get("next_account")) or 0))
    set_settings({"setup": {"next_account": n + 1}})
    return pre + str(n)


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
    if kind == "payment":
        data = clean_payment(data)
        touched = {a["claim_id"] for a in data["lines"]}
        if record_id:
            try:
                touched |= {a.get("claim_id") for a in vault.get(rid).get("lines") or []}
            except BaseException:
                pass
        data["saved_by"] = user
        vault.put(rid, data, KINDS[kind]["index"])
        after_payment(rid, data, touched, user)
        return {"id": rid, "data": data, **summary("payment", rid, data)}
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
    elif kind == "procedure":
        data = clean_procedure(data, rid)
    elif kind == "template":
        name = str(data.get("name") or "").strip()[:60]
        if not name:
            raise ValueError("a template needs a name")
        for oid, o in records("template"):
            if oid != rid and str(o.get("name") or "").strip().lower() == name.lower():
                raise ValueError(f"there is already a template called {name}")
        keep = ("code", "modifier", "m2", "m3", "m4", "description", "charge", "units", "pointer")
        data = {"name": name, "procedures": [{k: str((p or {}).get(k) or "") for k in keep} for p in (data.get("procedures") or [])[:6]
                                              if str((p or {}).get("code") or "").strip()],
                "diagnoses": [{"code": str((x or {}).get("code") or "")} for x in (data.get("diagnoses") or [])[:12] if (x or {}).get("code")],
                "place_of_service": str(data.get("place_of_service") or "")[:2]}
        if not data["procedures"]:
            raise ValueError("a template needs at least one service line with a code")
    elif kind == "task":
        if not str(data.get("subject") or "").strip():
            raise ValueError("a task needs a subject")
        if record_id is None:
            data["created_by"] = user
            data["created"] = time.strftime("%m/%d/%Y")
        data["done"] = data.get("status") == "Completed"
    else:
        if kind == "patient":
            last, first, mi = (str(data.get(k) or "").strip() for k in ("last_name", "first_name", "mi"))
            if last or first:
                data["patient_name"] = (last + ", " + first + (" " + mi if mi else "")).upper().strip(", ")
            acct = str(data.get("account_number") or "").strip()
            su = get_settings()["setup"]
            if not acct and su.get("auto_account", True):
                data["account_number"] = next_account_number()
            elif acct and su.get("unique_account", True):
                dup = [p for p in list_records("patient") if p.get("id") != rid and str(p.get("account_number") or "").strip() == acct]
                if dup:
                    raise ValueError(f"account number {acct} is already used by another patient")
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
            self.live[tok] = {"user": user, "created": now, "last": now, "company": None}
        return tok

    def company(self, tok: str) -> str | None:
        with self.lock:
            return (self.live.get(tok) or {}).get("company")

    def set_company(self, tok: str, name: str) -> None:
        with self.lock:
            if tok in self.live:
                self.live[tok]["company"] = name

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


# --------------------------------------------------------------------------
# company files (EZClaim's EZ button: New Company / Open Company)
# --------------------------------------------------------------------------
#
# In EZClaim a company file is a whole separate database: patients, claims,
# every library and every setting. A billing service keeps one per office and
# switches with Open Company; the title bar names the one that is open, and
# each user is allowed into particular companies. Here each company is its
# own vault directory. The first company is the original THUNDER_VAULT, so
# nothing moves when this is switched on. Encryption key: the same vault key
# for all of them (records are still encrypted one key per record).

COMPANIES_FILE = Path(os.environ.get("THUNDER_CLAIMS_COMPANIES",
                                     str(Path.home() / ".thunder" / "claims_companies.json")))
COMPANY_DIR = Path(os.environ.get("THUNDER_CLAIMS_COMPANY_DIR", str(vault.VAULT.parent / "vault-companies")))
COMPANY_RE = re.compile(r"^[A-Za-z0-9_]{2,40}$")  # EZClaim: letters, numbers and underscore only
_ctx = threading.local()


def load_companies() -> list[dict]:
    try:
        cs = json.loads(COMPANIES_FILE.read_text()).get("companies") or []
    except (FileNotFoundError, ValueError):
        cs = []
    if not cs:
        cs = [{"name": os.environ.get("THUNDER_CLAIMS_COMPANY", "Main"), "path": str(vault.VAULT), "default": True}]
    return cs


def save_companies(cs: list[dict]) -> None:
    COMPANIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = COMPANIES_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"companies": cs}, f, indent=2)
    os.replace(tmp, COMPANIES_FILE)


def company(name: str) -> dict | None:
    return next((c for c in load_companies() if c["name"].lower() == str(name or "").lower()), None)


def new_company(name: str) -> dict:
    name = str(name or "").strip()
    if not COMPANY_RE.match(name):
        raise ValueError("company names are letters, numbers and underscores only (2-40), e.g. Tampa_Office")
    if company(name):
        raise ValueError(f"there is already a company named {name}")
    cs = load_companies()
    path = COMPANY_DIR / name
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    c = {"name": name, "path": str(path), "created": time.strftime("%Y-%m-%d %H:%M")}
    save_companies(cs + [c])
    return c


def allowed_companies(user: str) -> list[str]:
    """A user's Company Permissions. Owners and users with no list (everyone
    before company files existed) may open all of them."""
    u = load_users().get(user) or {}
    names = [c["name"] for c in load_companies()]
    grant = u.get("companies")
    if u.get("role") == "owner" or grant in (None, "*"):
        return names
    return [n for n in names if n in grant]


def current_company() -> dict | None:
    return getattr(_ctx, "company", None)


PREFS_FILE = Path(os.environ.get("THUNDER_CLAIMS_PREFS",
                                 str(Path.home() / ".thunder" / "claims_prefs.json")))
PRINT_DEFAULTS = {"form": "preview", "dx": 0.0, "dy": 0.0, "vshift": 0.0, "hshift": 0.0,
                  "carrier_dx": 0.0, "carrier_dy": 0.0, "xdx": 0.02, "font": 12, "bottom_margin": False, "year4": False}


def get_prefs(user: str) -> dict:
    """Per-person printer settings for the red CMS-1500 forms (no patient data)."""
    try:
        allp = json.loads(PREFS_FILE.read_text())
    except (FileNotFoundError, ValueError):
        allp = {}
    return {"print": {**PRINT_DEFAULTS, **(allp.get(user, {}).get("print") or {})},
            "grids": allp.get(user, {}).get("grids") or {}}


def set_prefs(user: str, body: dict) -> dict:
    """Printer settings and grid layouts are per person, as in EZClaim (each
    desk has its own printer; each person arranges their own columns). Either
    part can be sent alone."""
    try:
        allp = json.loads(PREFS_FILE.read_text())
    except (FileNotFoundError, ValueError):
        allp = {}
    mine = allp.setdefault(user, {})
    if "grids" in (body or {}):
        grids = {}
        for kind, cols in ((body or {}).get("grids") or {}).items():
            if kind in KINDS and isinstance(cols, list):
                keep = [str(k)[:24] for k in cols if re.fullmatch(r"[a-z0-9_]{1,24}", str(k))][:30]
                if keep:
                    grids[kind] = keep
        mine["grids"] = grids
    if "print" in (body or {}):
        mine["print"] = _clean_print((body or {}).get("print") or {})
    PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = PREFS_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(allp, f, indent=2)
    os.replace(tmp, PREFS_FILE)
    return get_prefs(user)


def _clean_print(src: dict) -> dict:
    pr = dict(PRINT_DEFAULTS)
    if src.get("form") in ("preview", "always", "never"):
        pr["form"] = src["form"]
    for k in ("dx", "dy", "carrier_dx", "carrier_dy"):  # inches, a sheet's worth either way at most
        pr[k] = max(-1.0, min(1.0, round(money(src.get(k)), 3)))
    pr["xdx"] = max(-0.2, min(0.2, round(money(src.get("xdx", PRINT_DEFAULTS["xdx"])), 3)))  # check-box X nudge
    for k in ("vshift", "hshift"):                      # percent stretch across the page
        pr[k] = max(-5.0, min(5.0, round(money(src.get(k)), 2)))
    pr["font"] = int(src.get("font")) if str(src.get("font")) in ("10", "11", "12") else 12
    pr["bottom_margin"] = bool(src.get("bottom_margin"))
    pr["year4"] = bool(src.get("year4"))
    return pr


def access_log(who: str, ip: str, method: str, path: str, status: int) -> None:
    """Who asked for what, from where. Record ids only - no names, so the log
    is not itself PHI."""
    c = current_company()
    line = json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "who": who, "ip": ip,
                       "company": c["name"] if c else "", "method": method, "path": path[:200], "status": status})
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
            if who != "anonymous":
                name = SESSIONS.company(self._token())
                ok = allowed_companies(who)
                c = company(name) if name in ok else None
                if c is None and not u.path.startswith("/api/compan") and u.path not in ("/api/whoami", "/api/logout"):
                    return self._send(409, {"error": "open a company first", "companies": ok})
                if c:
                    _ctx.company = c
                    vault.set_root(c["path"])
            (self._get if method == "GET" else self._post)(u, who, ip)
        except ValueError as e:
            self._send(400, {"error": str(e)})
        except BaseException as e:
            self._send(500, {"error": str(e).splitlines()[0] if str(e) else type(e).__name__})
        finally:
            vault.set_actor(None)
            vault.set_root(None)
            if u.path not in ("/", "/index.html"):
                access_log(who, ip, method, u.path + ("?" + u.query if u.query else ""), self._status)
            _ctx.company = None

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def _get(self, u, who, ip):
        if u.path in ("/", "/index.html"):
            return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/prefs":
            return self._send(200, get_prefs(who))
        if u.path == "/api/whoami":
            c = current_company()
            return self._send(200, {"user": who, "idle_minutes": IDLE_SECONDS // 60, "company": c["name"] if c else None})
        if u.path == "/api/companies":
            c = current_company()
            return self._send(200, {"current": c["name"] if c else None, "companies": allowed_companies(who),
                                    "can_create": (load_users().get(who) or {}).get("role") == "owner"})
        if u.path == "/api/list":
            kind = (parse_qs(u.query).get("kind") or ["claim"])[0]
            if kind not in KINDS:
                return self._send(400, {"error": "unknown record type"})
            return self._send(200, {"records": list_records(kind)})
        if u.path == "/api/settings":
            return self._send(200, get_settings())
        if u.path == "/api/users":
            return self._send(200, {"users": sorted(n for n, x in load_users().items() if not x.get("disabled"))})
        if u.path == "/api/find":
            return self._send(200, reports.find(sys.modules[__name__], (parse_qs(u.query).get("what") or [""])[0]))
        if u.path == "/api/reports":
            return self._send(200, reports.catalogue(sys.modules[__name__]))
        if u.path == "/api/statements":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            return self._send(200, {"rows": statement_list(money(q.get("min", "0.01")), int(money(q.get("cycle", "30"))), q.get("zero") == "1")})
        m = re.match(r"^/api/statement/([A-Za-z0-9_-]+)$", u.path)
        if m:
            return self._send(200, statement_detail(m.group(1)))
        if u.path == "/api/open_lines":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            return self._send(200, {"lines": open_lines(q.get("source", "payer"), q.get("payer", ""), q.get("patient", ""),
                                                        q.get("patient_name", ""), q.get("ignore") == "1", q.get("zero") == "1",
                                                        q.get("payment") or None)})
        m = re.match(r"^/api/rec/([A-Za-z0-9_-]+)$", u.path)
        if m:
            rid = m.group(1)
            r = vault.get(rid)
            kind = kind_of(rid)
            body = {"id": rid, "kind": kind, "data": r}
            if kind == "patient":
                body["benefits"] = patient_benefits(rid, r)
            if kind == "claim" and ID_RE.match(str(r.get("patient_id") or "")) and vault.record_path(r["patient_id"]).exists():
                body["benefits"] = patient_benefits(r["patient_id"], vault.get(r["patient_id"]))
            if kind == "claim":
                body.update(assess(r))
                full = ledger()
                led = full.get(rid) or {"paid": 0.0, "adj": 0.0, "pr": 0.0, "pat_paid": 0.0, "lines": {}}
                body["ledger"] = {"paid": led["paid"], "adj": led["adj"], "pr": led["pr"], "pat_paid": led["pat_paid"],
                                  "lines": {str(k): v for k, v in led["lines"].items()},
                                  "split": {str(x["line"]): {"pat_bal": x["pat_bal"], "ins_bal": x["ins_bal"]} for x in claim_lines(rid, r, full)}}
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
            ok = allowed_companies(name)
            last = (load_users().get(name) or {}).get("last_company")
            pick = last if last in ok else (ok[0] if ok else None)
            SESSIONS.set_company(tok, pick)
            return self._send(200, {"token": tok, "user": name, "idle_minutes": IDLE_SECONDS // 60,
                                    "company": pick, "companies": ok})
        if u.path == "/api/logout":
            SESSIONS.end(self._token())
            return self._send(200, {"ok": True})
        if u.path in ("/api/company/open", "/api/company/new"):
            b = json.loads(self._body() or b"{}")
            if u.path.endswith("/new"):
                if (load_users().get(who) or {}).get("role") != "owner":
                    return self._send(403, {"error": "only the owner can create a company"})
                name = new_company(b.get("name"))["name"]
            else:
                c = company(b.get("name"))
                if not c or c["name"] not in allowed_companies(who):
                    return self._send(403, {"error": "you do not have permission for that company"})
                name = c["name"]
            SESSIONS.set_company(self._token(), name)
            users = load_users()
            if who in users:
                users[who]["last_company"] = name
                save_users(users)
            return self._send(200, {"company": name})
        if u.path == "/api/prefs":
            return self._send(200, set_prefs(who, json.loads(self._body() or b"{}")))
        if u.path == "/api/settings":
            return self._send(200, set_settings(json.loads(self._body() or b"{}")))
        if u.path == "/api/statements/printed":
            b = json.loads(self._body() or b"{}")
            return self._send(200, {"updated": statements_printed(b.get("items") or [], str(b.get("date") or time.strftime("%m/%d/%Y"))[:10], who)})
        if u.path == "/api/benefits":
            b = json.loads(self._body() or b"{}")
            pid = str(b.get("id") or "")
            if pid and not (ID_RE.match(pid) and kind_of(pid) == "patient"):
                return self._send(400, {"error": "bad record id"})
            return self._send(200, patient_benefits(pid, b.get("data") or {}))
        if u.path == "/api/print_check":
            b = json.loads(self._body() or b"{}")
            out = []
            for cid in (b.get("ids") or [])[:500]:
                if ID_RE.match(str(cid)) and kind_of(cid) == "claim" and vault.record_path(cid).exists():
                    c = vault.get(cid)
                    for r in print_check(cid, c):
                        out.append({"id": cid, "name": c.get("patient_name", ""), "dob": c.get("dob", ""), "account": c.get("account_number", ""),
                                    "dos": c.get("date_of_service", ""), "proc": " ".join(str(p.get("code") or "") for p in c.get("procedures") or [] if (p or {}).get("code")), **r})
            return self._send(200, {"rows": out})
        if u.path == "/api/claims/printed":
            b = json.loads(self._body() or b"{}")
            return self._send(200, {"updated": claims_printed(b.get("ids") or [], str(b.get("date") or time.strftime("%m/%d/%Y"))[:10], who)})
        if u.path == "/api/delete":
            b = json.loads(self._body() or b"{}")
            return self._send(200, delete_record(str(b.get("id") or ""), who))
        if u.path == "/api/merge":
            b = json.loads(self._body() or b"{}")
            return self._send(200, merge_patients(str(b.get("keep") or ""), str(b.get("drop") or ""), who))
        if u.path == "/api/writeoff":
            b = json.loads(self._body() or b"{}")
            return self._send(200, write_off(str(b.get("id") or ""), str(b.get("group") or "CO"), str(b.get("reason") or "45"), who))
        if u.path == "/api/password":
            b = json.loads(self._body() or b"{}")
            if SESSIONS.locked("u:" + who):
                return self._send(429, {"error": "too many wrong passwords - try again later"})
            if not verify_password(who, str(b.get("old") or "")):
                SESSIONS.failed("u:" + who)
                return self._send(403, {"error": "the current password is wrong"})
            set_password(who, str(b.get("new") or ""))
            return self._send(200, {"ok": True})
        if u.path == "/api/report":
            b = json.loads(self._body() or b"{}")
            return self._send(200, reports.run(sys.modules[__name__], str(b.get("name") or ""), b.get("criteria") or {}))
        if u.path == "/api/procedures/from_claims":
            return self._send(200, procedures_from_claims(who))
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
    ap.add_argument("cmd", choices=["users", "adduser", "passwd", "disable", "enable",
                                    "companies", "newcompany", "grant", "revoke"])
    ap.add_argument("name", nargs="?")
    ap.add_argument("company", nargs="?", help="grant/revoke: a company name, or * for all")
    a = ap.parse_args(argv)
    users = load_users()
    if a.cmd == "companies":
        for c in load_companies():
            who = [n for n in sorted(users) if c["name"] in allowed_companies(n)]
            print(f"{c['name']:24} {c['path']}\n{'':24} users: {', '.join(who) or '-'}")
        return 0
    if a.cmd == "newcompany":
        try:
            c = new_company(a.name)
        except ValueError as e:
            raise SystemExit(str(e))
        print(f"created company {c['name']} at {c['path']}")
        return 0
    if a.cmd in ("grant", "revoke"):
        if a.name not in users or not a.company:
            raise SystemExit(f"usage: {a.cmd} <user> <company|*>")
        u = users[a.name]
        if a.company == "*":
            u["companies"] = "*" if a.cmd == "grant" else []
        else:
            c = company(a.company)
            if not c:
                raise SystemExit(f"no company {a.company}")
            have = [n for n in allowed_companies(a.name)] if u.get("companies") in (None, "*") else list(u["companies"])
            have = sorted(set(have) | {c["name"]}) if a.cmd == "grant" else [n for n in have if n != c["name"]]
            u["companies"] = have
        save_users(users)
        print(f"{a.name}: {', '.join(allowed_companies(a.name)) or 'no companies'}"
              + (" (owner - always all)" if u.get("role") == "owner" else ""))
        return 0
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
    if len(sys.argv) > 1 and sys.argv[1] in ("users", "adduser", "passwd", "disable", "enable", "companies", "newcompany", "grant", "revoke"):
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
