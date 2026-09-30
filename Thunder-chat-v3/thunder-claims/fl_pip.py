"""Florida PIP deadlines for one claim - Fla. Stat. 627.736.

The office bills only auto-insurance Personal Injury Protection in Florida,
so every claim lives or dies by a handful of clocks in that statute:

- 627.736(1)(a): PIP pays only if the *initial* services were within 14 days
  of the accident.
- 627.736(5)(c): a bill may not include services more than 35 days before its
  postmark - 75 days if a notice of initiation of treatment went to the
  insurer within 21 days of the first treatment.
- 627.736(4)(b): benefits are overdue if not paid within 30 days of the
  insurer receiving written notice. If the insurer gave notice that it is
  investigating the claim, it has until day 90 to pay or deny.
- 627.736(10): a demand letter is a precondition to suit, and may be sent
  only once the claim is overdue.

Everything here is arithmetic on dates the office typed in. It is a reminder
system, not legal advice: the statute and the office's attorney decide.
"""
from __future__ import annotations

from datetime import date, timedelta

import validate

INITIAL_CARE_DAYS = 14
FILE_DAYS = 35
FILE_DAYS_WITH_NOTICE = 75
NOTICE_DAYS = 21
PAY_DAYS = 30
PAY_DAYS_INVESTIGATED = 90
SOON = 7  # days: "coming up" rather than "fine"

# worst first; the claim's level is the worst of its items
LEVELS = ("late", "overdue", "soon", "ok")


def _d(s) -> date | None:
    return validate.parse_date(str(s or "")) if s else None


def _mdy(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def service_dates(c: dict) -> list[date]:
    out = []
    for p in c.get("procedures") or []:
        if not str((p or {}).get("code") or "").strip():
            continue
        d = _d(p.get("date")) or _d(c.get("date_of_service"))
        if d:
            out.append(d)
    if not out and _d(c.get("date_of_service")):
        out.append(_d(c.get("date_of_service")))
    return out


def applies(c: dict) -> bool:
    """Every claim is Florida PIP unless it says otherwise (box 10b)."""
    st = str(c.get("accident_state") or "").strip().upper()
    return st in ("", "FL")


def deadlines(c: dict, today: date | None = None) -> dict:
    today = today or date.today()
    if not applies(c):
        return {"applies": False, "level": "", "items": [], "flags": [], "text": ""}
    tr = c.get("tracking") or {}
    billing = tr.get("billing") or "draft"
    items, flags = [], []

    def item(key, label, when, level, note=""):
        items.append({"key": key, "label": label, "date": _mdy(when), "days": (when - today).days,
                      "level": level, "note": note})

    def flag(key, level, text):
        flags.append({"key": key, "level": level, "text": text})

    dos = service_dates(c)
    doi = _d(c.get("date_of_injury"))
    first_tx = _d(c.get("first_treatment")) or (min(dos) if dos else None)
    notice = _d(c.get("pip_notice_sent"))

    # 1. initial care within 14 days of the accident
    if doi and first_tx:
        gap = (first_tx - doi).days
        if gap < 0:
            flag("dates", "late", f"First treatment {_mdy(first_tx)} is before the date of injury {_mdy(doi)} - check the dates.")
        elif gap > INITIAL_CARE_DAYS:
            flag("initial", "late", f"First treatment was {gap} days after the accident. PIP pays only if initial "
                         f"services were within {INITIAL_CARE_DAYS} days (627.736(1)(a)).")
    elif not doi:
        flag("no_doi", "soon", "No date of injury - the 14-day and filing rules cannot be checked.")

    # 2. the filing window: 35 days, or 75 with a timely notice of initiation
    notice_ok = bool(notice and first_tx and 0 <= (notice - first_tx).days <= NOTICE_DAYS)
    window = FILE_DAYS_WITH_NOTICE if notice_ok else FILE_DAYS
    if notice and first_tx and not notice_ok:
        flag("notice_late", "soon", f"Notice of initiation was sent {(notice - first_tx).days} days after first treatment "
                     f"(needs {NOTICE_DAYS} or fewer), so the {FILE_DAYS}-day limit applies.")
    if not notice and first_tx and billing in ("draft", "hold"):
        by = first_tx + timedelta(days=NOTICE_DAYS)
        if by >= today:
            item("notice", "Send notice of initiation by", by, "soon" if (by - today).days <= SOON else "ok",
                 f"extends billing from {FILE_DAYS} to {FILE_DAYS_WITH_NOTICE} days")
    sent = _d(tr.get("sent_date"))
    if dos:
        oldest = min(dos)
        bill_by = oldest + timedelta(days=window)
        if sent:
            late = sorted({d for d in dos if (sent - d).days > window})
            if late:
                flag("billed_late", "late", f"Billed {_mdy(sent)}: {len(late)} service date(s) from {_mdy(late[0])} were more than "
                             f"{window} days before the postmark (627.736(5)(c)).")
        elif billing in ("draft", "hold"):
            left = (bill_by - today).days
            item("file", "Postmark bill by", bill_by, "late" if left < 0 else "soon" if left <= SOON else "ok",
                 f"{window} days from {_mdy(oldest)}" + (" (notice sent)" if notice_ok else ""))
            if left < 0:
                flag("file_late", "late", f"The bill is {-left} days past the {window}-day limit for {_mdy(oldest)}. "
                             "Those services can no longer be billed to PIP.")

    # 3. the carrier's clock: 30 days from receipt, 90 if they are investigating
    if billing == "sent" and not sent:
        flag("no_sent", "soon", "Submitted, but no Original Bill Date - the carrier's 30 days cannot be counted.")
    if sent and billing == "sent":
        rec = _d(tr.get("received_date"))
        investigated = _d(tr.get("fraud_notice"))
        base = rec or sent
        due = base + timedelta(days=PAY_DAYS_INVESTIGATED if investigated else PAY_DAYS)
        left = (due - today).days
        note = (f"{PAY_DAYS_INVESTIGATED if investigated else PAY_DAYS} days from "
                + ("receipt" if rec else "the bill date - enter the received date for the exact day"))
        item("pay", "Carrier must pay by", due, "overdue" if left < 0 else "soon" if left <= SOON else "ok", note)
        if left < 0:
            flag("overdue", "overdue", f"Payment is {-left} days overdue. A demand letter (627.736(10)) may now be sent.")

    worst = [x["level"] for x in items + flags]
    level = next((lv for lv in LEVELS if lv in worst), "")
    return {"applies": True, "level": level, "items": items, "flags": flags, "text": short(items, flags),
            "window": window}


def short(items: list, flags: list) -> str:
    """One cell's worth for the claims grid, most urgent first."""
    by = {i["key"]: i for i in items}
    fk = {f["key"] for f in flags}
    if "pay" in by and by["pay"]["days"] < 0:
        return f"Overdue {-by['pay']['days']}d"
    if "file" in by:
        d = by["file"]["days"]
        return f"Late {-d}d" if d < 0 else f"Bill in {d}d"
    for key, text in (("billed_late", "Billed late"), ("initial", "Care >14d"), ("dates", "Check dates"),
                      ("no_doi", "No injury date"),
                      ("no_sent", "No bill date")):
        if key in fk:
            return text
    if "pay" in by:
        return f"Pay due {by['pay']['days']}d"
    return ""
