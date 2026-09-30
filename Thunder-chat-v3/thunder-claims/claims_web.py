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
}
BILLING = ("draft", "sent", "hold", "paid", "partial", "denied")
METHODS = ("CHECK", "EFT", "CASH", "CREDIT CARD", "MONEY ORDER", "OTHER")
FIRST_ACCOUNT = 1000  # EZClaim numbers patients from 1000 up


def kind_of(record_id: str) -> str:
    for k in ("patient", "payer", "provider", "payment"):
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


def summary(kind: str, rid: str, r: dict, led: dict | None = None) -> dict:
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
                "pip_level": pip["level"], "pip_text": pip["text"],
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
    led = ledger() if kind == "claim" else None
    for p in sorted(vault.records_dir().glob("*.rec"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        if kind_of(p.stem) != kind:
            continue
        try:
            r = vault.get(p.stem)
        except BaseException as e:  # vault raises SystemExit on a bad record
            out.append({"id": p.stem, "error": str(e).splitlines()[0]})
            continue
        out.append(summary(kind, p.stem, r, led))
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


def get_settings() -> dict:
    """Practice-wide options (return address and the like) - no patient data."""
    try:
        s_ = json.loads(SETTINGS_FILE.read_text())
    except (FileNotFoundError, ValueError):
        s_ = {}
    return {"statement": {**STATEMENT_DEFAULTS, **(s_.get("statement") or {})}}


def set_settings(body: dict) -> dict:
    cur = get_settings()["statement"]
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
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"statement": cur}, f, indent=2)
    os.replace(tmp, SETTINGS_FILE)
    return {"statement": cur}


def _norm(x) -> str:
    return str(x or "").strip().upper()


def patient_claims(pid: str, p: dict, claims: list) -> list:
    return [(cid, c) for cid, c in claims
            if (c.get("patient_id") == pid) or (not c.get("patient_id") and _norm(c.get("patient_name")) == _norm(p.get("patient_name")))]


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
    return {"print": {**PRINT_DEFAULTS, **(allp.get(user, {}).get("print") or {})}}


def set_prefs(user: str, body: dict) -> dict:
    pr = dict(PRINT_DEFAULTS)
    src = (body or {}).get("print") or {}
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
    try:
        allp = json.loads(PREFS_FILE.read_text())
    except (FileNotFoundError, ValueError):
        allp = {}
    allp.setdefault(user, {})["print"] = pr
    PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = PREFS_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(allp, f, indent=2)
    os.replace(tmp, PREFS_FILE)
    return {"print": pr}


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
        if u.path == "/api/prefs":
            return self._send(200, get_prefs(who))
        if u.path == "/api/whoami":
            return self._send(200, {"user": who, "idle_minutes": IDLE_SECONDS // 60})
        if u.path == "/api/list":
            kind = (parse_qs(u.query).get("kind") or ["claim"])[0]
            if kind not in KINDS:
                return self._send(400, {"error": "unknown record type"})
            return self._send(200, {"records": list_records(kind)})
        if u.path == "/api/settings":
            return self._send(200, get_settings())
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
            return self._send(200, {"token": tok, "user": name, "idle_minutes": IDLE_SECONDS // 60})
        if u.path == "/api/logout":
            SESSIONS.end(self._token())
            return self._send(200, {"ok": True})
        if u.path == "/api/prefs":
            return self._send(200, set_prefs(who, json.loads(self._body() or b"{}")))
        if u.path == "/api/settings":
            return self._send(200, set_settings(json.loads(self._body() or b"{}")))
        if u.path == "/api/statements/printed":
            b = json.loads(self._body() or b"{}")
            return self._send(200, {"updated": statements_printed(b.get("items") or [], str(b.get("date") or time.strftime("%m/%d/%Y"))[:10], who)})
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
