"""Reports - EZClaim's Reports tab, rebuilt.

EZClaim ships a report *engine* with a `Report Criteria` panel, and the
reports themselves are definitions: a name, a one-line description, the
criteria it takes, and what it prints. This module is the same shape. Each
report returns the same generic structure, which the page renders, prints and
drills down from:

    {"title", "landscape", "columns": [{"k", "t", "m"}],
     "rows": [{"level", "bold", "cells": {k: value}, "open": {"kind", "id"}}],
     "totals": {k: value}, "totals_label", "echo"}

Money is printed EZClaim's way by the page (no "$" inside the table, zero as
".00"). The criteria echo line goes on the paper, so a printed report always
says what it was filtered on.

Every number here is computed from the vault at the moment the report runs;
nothing is cached or stored.
"""
from __future__ import annotations

from datetime import date, timedelta

import fl_pip
import validate

# ---------------------------------------------------------------------------
# criteria building blocks (the page draws the panel from these)
# ---------------------------------------------------------------------------

GROUP_CLAIM = ["None", "Claim Primary Payer", "Claim Rendering Provider", "Claim Billing Provider", "Claim Status"]
STATUS_NAMES = {"draft": "Ready to Submit", "sent": "Submitted", "hold": "On Hold", "partial": "Partly Paid",
                "paid": "Paid", "denied": "Denied"}


def _d(s):
    return validate.parse_date(str(s or "")) if s else None


def _mdy(d):
    return d.strftime("%m/%d/%Y") if d else ""


def _in(d, start, end) -> bool:
    if not (start or end):
        return True
    if d is None:
        return False
    return (not start or d >= start) and (not end or d <= end)


def _rng(crit: dict, key: str):
    return _d(crit.get(key + "_start")), _d(crit.get(key + "_end"))


def _echo(spec: list, crit: dict) -> str:
    out = []
    for c in spec:
        k, label, typ = c["k"], c["label"], c["type"]
        if typ == "daterange":
            s, e = crit.get(k + "_start"), crit.get(k + "_end")
            if s or e:
                out.append(f"{label}: {s or 'No Start Date'} - {e or 'No End Date'}")
        elif typ == "check":
            out.append(f"{label}: {'Checked' if crit.get(k) else 'Unchecked'}")
        else:
            v = crit.get(k)
            out.append(f"{label}: {v if v not in (None, '') else 'All' if typ == 'select' else 'None'}")
    return ", ".join(out)


# ---------------------------------------------------------------------------
# one pass over the vault: every claim, with its money worked out
# ---------------------------------------------------------------------------

def claim_facts(cw) -> list[dict]:
    led = cw.ledger()
    out = []
    for cid, c in cw.records("claim"):
        tr = c.get("tracking") or {}
        lines = cw.claim_lines(cid, c, led)
        posted = led.get(cid) or {"paid": 0.0, "adj": 0.0, "pat_paid": 0.0}
        manual = cw.money(tr.get("paid_amount"))
        charges = cw.total_charges(c)
        pat_paid = posted.get("pat_paid", 0.0)
        ins_paid = round(posted["paid"] - pat_paid + manual, 2)
        dates = [d for d in (_d(x["date"]) for x in lines) if d]
        pay_dates = [d for d in (_d(e["date"]) for x in lines for e in x["entries"]) if d]
        balance = round(charges - posted["paid"] - manual - posted["adj"], 2)
        paid_date = _d(tr.get("paid_date")) or (max(pay_dates) if pay_dates and balance <= 0.004 else None)
        created = next((n.get("ts", "")[:10] for n in c.get("notes_log") or [] if n.get("ts")), "")
        out.append({
            "id": cid, "c": c, "lines": lines,
            "patient": c.get("patient_name", ""), "patient_id": c.get("patient_id", ""),
            "account": c.get("account_number", ""), "dob": c.get("dob", ""), "insured_id": c.get("claim_number", ""),
            "payer": c.get("insurer", "") or "(no payer)", "rendering": c.get("treating_provider", "") or "RENDERING NOT SELECTED",
            "billing_prov": c.get("clinic_name", "") or "BILLING NOT SELECTED",
            "status": STATUS_NAMES.get(tr.get("billing") or "draft", tr.get("billing") or ""), "billing": tr.get("billing") or "draft",
            "dx": " ".join(str((d or {}).get("code") or "") for d in (c.get("diagnoses") or [])[:4] if (d or {}).get("code")),
            "first_dos": min(dates) if dates else _d(c.get("date_of_service")),
            "bill_date": _d(tr.get("sent_date")), "paid_date": paid_date, "created": _d(created),
            "charges": charges, "ins_paid": ins_paid, "pat_paid": round(pat_paid, 2), "adj": round(posted["adj"], 2),
            "balance": balance, "units": sum(int(cw.money(p.get("units")) or 1) for p in c.get("procedures") or [] if (p or {}).get("code")),
            "pip": fl_pip.deadlines(c),
        })
    return out


def _group_key(f: dict, by: str) -> str:
    return {"Claim Primary Payer": f["payer"], "Claim Rendering Provider": f["rendering"],
            "Claim Billing Provider": f["billing_prov"], "Claim Status": f["status"]}.get(by, "")


def _sum(rows: list, keys: list) -> dict:
    return {k: round(sum(r.get(k) or 0 for r in rows), 2) for k in keys}


# ---------------------------------------------------------------------------
# the reports
# ---------------------------------------------------------------------------

CLAIM_LIST_CRIT = [
    {"k": "group_by", "label": "Group By", "type": "select", "options": GROUP_CLAIM, "section": "General"},
    {"k": "detail", "label": "Show Service Line Detail", "type": "check", "section": "General"},
    {"k": "bill_date", "label": "Original Bill Date", "type": "daterange", "section": "Dates"},
    {"k": "paid_date", "label": "Claim Paid Date", "type": "daterange", "section": "Dates"},
    {"k": "first_dos", "label": "1st DOS", "type": "daterange", "section": "Dates"},
    {"k": "payer", "label": "Claim Primary Payer", "type": "select", "options": "payers", "section": "Claim"},
    {"k": "rendering", "label": "Claim Rendering Provider", "type": "select", "options": "providers", "section": "Claim"},
    {"k": "status", "label": "Claim Status", "type": "select", "options": list(STATUS_NAMES.values()), "section": "Claim"},
    {"k": "min_balance", "label": "Claim Minimum Balance", "type": "money", "section": "Claim"},
]


def _claim_filter(facts: list, crit: dict) -> list:
    out = []
    mb = crit.get("min_balance")
    for f in facts:
        if not _in(f["bill_date"], *_rng(crit, "bill_date")) or not _in(f["paid_date"], *_rng(crit, "paid_date")) \
                or not _in(f["first_dos"], *_rng(crit, "first_dos")):
            continue
        if crit.get("payer") and f["payer"] != crit["payer"]:
            continue
        if crit.get("rendering") and f["rendering"] != crit["rendering"]:
            continue
        if crit.get("status") and f["status"] != crit["status"]:
            continue
        if mb not in (None, "") and f["balance"] < float(mb):
            continue
        out.append(f)
    return out


def claim_list(cw, crit: dict) -> dict:
    """EZClaim's own trainers use this, not the A/R report, for receivables:
    claims grouped under the patient, with totals at every level."""
    money_cols = ["charges", "pat_paid", "ins_paid", "adj", "balance"]
    cols = [{"k": "name", "t": "Name"}, {"k": "inv", "t": "Inv # or ID"}, {"k": "diag", "t": "Diag"},
            {"k": "dos", "t": "1st DOS"}, {"k": "bill", "t": "Bill Date"}, {"k": "paid", "t": "Paid Date"},
            {"k": "charges", "t": "Charges", "m": 1}, {"k": "pat_paid", "t": "Pat Pmts", "m": 1},
            {"k": "ins_paid", "t": "Ins Pmts", "m": 1}, {"k": "adj", "t": "Adjs", "m": 1}, {"k": "balance", "t": "Balance", "m": 1}]
    facts = sorted(_claim_filter(claim_facts(cw), crit), key=lambda f: (f["patient"], f["first_dos"] or date.min))
    by = crit.get("group_by") or "None"
    rows = []
    groups: dict = {}
    for f in facts:
        groups.setdefault(_group_key(f, by) if by != "None" else "", []).append(f)
    for g in sorted(groups):
        members = groups[g]
        lvl = 0
        if by != "None":
            rows.append({"level": 0, "bold": 1, "cells": {"name": g, **_sum(members, money_cols)}})
            lvl = 1
        pats: dict = {}
        for f in members:
            pats.setdefault((f["patient"], f["patient_id"]), []).append(f)
        for (pname, pid), fs in sorted(pats.items()):
            rows.append({"level": lvl, "cells": {"name": pname, **_sum(fs, money_cols)},
                         "open": {"kind": "patient", "id": pid} if pid else None})
            for f in fs:
                rows.append({"level": lvl + 1, "bold": 1, "open": {"kind": "claim", "id": f["id"]},
                             "cells": {"name": "", "inv": f["account"] or f["id"][-8:], "diag": f["dx"], "dos": _mdy(f["first_dos"]),
                                       "bill": _mdy(f["bill_date"]), "paid": _mdy(f["paid_date"]),
                                       **{k: f[k] for k in money_cols}}})
                if crit.get("detail"):
                    for x in f["lines"]:
                        rows.append({"level": lvl + 2, "open": {"kind": "claim", "id": f["id"]},
                                     "cells": {"inv": x["date"], "diag": x["code"], "dos": x["description"][:24],
                                               "charges": x["charge"], "ins_paid": x["paid"], "adj": x["adj"], "balance": x["balance"]}})
    return {"columns": cols, "rows": rows, "totals": _sum(facts, money_cols),
            "totals_label": f"Grand Totals    Claim Count: {len(facts)}    Units: {sum(f['units'] for f in facts)}"}


AGING = [("0-30", 0, 30), ("31-60", 31, 60), ("61-90", 61, 90), ("91-120", 91, 120), ("Over 120", 121, 10 ** 6)]

AR_CRIT = [
    {"k": "aging_date", "label": "Aging as of Date", "type": "date", "section": "General"},
    {"k": "group_by", "label": "Group By", "type": "select", "options": ["Claim Primary Payer", "None", "Claim Rendering Provider"], "section": "General"},
    {"k": "by_dos", "label": "Calculate Aging by DOS", "type": "check", "section": "General"},
    {"k": "hide_detail", "label": "Hide Detail", "type": "check", "section": "General"},
    {"k": "payer", "label": "Claim Primary Payer", "type": "select", "options": "payers", "section": "Claim"},
]


def accounts_receivable(cw, crit: dict) -> dict:
    """Aging = Aging as of Date - Original Bill Date (DOS when there is no bill
    date, or when Calculate Aging by DOS is ticked). Payments and adjustments
    dated after the aging date are not counted, as in EZClaim."""
    asof = _d(crit.get("aging_date")) or date.today()
    buckets = [a[0] for a in AGING]
    cols = [{"k": "name", "t": "Payer / Patient"}, {"k": "dos", "t": "1st DOS"}, {"k": "bill", "t": "Bill Date"},
            *[{"k": b, "t": b, "m": 1} for b in buckets], {"k": "total", "t": "Total", "m": 1}]
    by = crit.get("group_by") or "Claim Primary Payer"
    items = []
    for f in claim_facts(cw):
        if crit.get("payer") and f["payer"] != crit["payer"]:
            continue
        if f["first_dos"] and f["first_dos"] > asof:
            continue
        later = sum(e["paid"] + e["adj"] for x in f["lines"] for e in x["entries"] if (_d(e["date"]) or date.min) > asof)
        bal = round(f["balance"] + later, 2)
        if abs(bal) < 0.005:
            continue
        start = f["first_dos"] if crit.get("by_dos") or not f["bill_date"] else f["bill_date"]
        age = (asof - start).days if start else 0
        b = next(a[0] for a in AGING if a[1] <= max(age, 0) <= a[2])
        items.append({"f": f, "cells": {b: bal, "total": bal}})
    rows, groups = [], {}
    for it in items:
        groups.setdefault(_group_key(it["f"], by) if by != "None" else "", []).append(it)
    keys = buckets + ["total"]
    for g in sorted(groups):
        tot = {k: round(sum(i["cells"].get(k, 0) for i in groups[g]), 2) for k in keys}
        if by != "None":
            rows.append({"level": 0, "bold": 1, "cells": {"name": g, **tot}})
        if not crit.get("hide_detail"):
            for it in sorted(groups[g], key=lambda i: (i["f"]["patient"], i["f"]["first_dos"] or date.min)):
                f = it["f"]
                rows.append({"level": 1 if by != "None" else 0, "open": {"kind": "claim", "id": f["id"]},
                             "cells": {"name": f["patient"], "dos": _mdy(f["first_dos"]), "bill": _mdy(f["bill_date"]), **it["cells"]}})
    totals = {k: round(sum(i["cells"].get(k, 0) for i in items), 2) for k in keys}
    return {"columns": cols, "rows": rows, "totals": totals, "landscape": 1,
            "totals_label": f"Grand Totals    Claim Count: {len(items)}    Aging as of {_mdy(asof)}"}


FOLLOWUP_CRIT = [
    {"k": "aging_date", "label": "Aging as of Date", "type": "date", "section": "General"},
    {"k": "payer", "label": "Claim Primary Payer", "type": "select", "options": "payers", "section": "Claim"},
    {"k": "min_days", "label": "Minimum Days Since Billed", "type": "number", "section": "Claim"},
    {"k": "min_balance", "label": "Claim Minimum Balance", "type": "money", "section": "Claim"},
]


def insurance_followup(cw, crit: dict) -> dict:
    """What each carrier still owes, oldest first, with the PIP clock -
    the report to work from when phoning adjusters."""
    asof = _d(crit.get("aging_date")) or date.today()
    mind = int(float(crit.get("min_days") or 0))
    mb = float(crit.get("min_balance") or 0.01)
    cols = [{"k": "name", "t": "Patient"}, {"k": "dob", "t": "DOB"}, {"k": "insured", "t": "Claim / Insured ID"},
            {"k": "dos", "t": "1st DOS"}, {"k": "bill", "t": "Bill Date"}, {"k": "days", "t": "Days"},
            {"k": "codes", "t": "Codes"}, {"k": "status", "t": "Status"}, {"k": "pip", "t": "PIP Clock"},
            {"k": "charges", "t": "Charges", "m": 1}, {"k": "ins_paid", "t": "Paid", "m": 1}, {"k": "balance", "t": "Balance", "m": 1}]
    by_payer: dict = {}
    for f in claim_facts(cw):
        if f["billing"] in ("draft", "paid") or f["balance"] < mb:
            continue
        if crit.get("payer") and f["payer"] != crit["payer"]:
            continue
        start = f["bill_date"] or f["first_dos"]
        days = (asof - start).days if start else 0
        if days < mind:
            continue
        by_payer.setdefault(f["payer"], []).append((days, f))
    rows, all_f = [], []
    for payer in sorted(by_payer):
        fs = sorted(by_payer[payer], key=lambda x: -x[0])
        all_f += [f for _, f in fs]
        rows.append({"level": 0, "bold": 1, "cells": {"name": payer, **_sum([f for _, f in fs], ["charges", "ins_paid", "balance"])}})
        for days, f in fs:
            rows.append({"level": 1, "open": {"kind": "claim", "id": f["id"]},
                         "cells": {"name": f["patient"], "dob": f["dob"], "insured": f["insured_id"], "dos": _mdy(f["first_dos"]),
                                   "bill": _mdy(f["bill_date"]), "days": str(days),
                                   "codes": " ".join(x["code"] for x in f["lines"])[:28], "status": f["status"],
                                   "pip": f["pip"].get("text", ""), "charges": f["charges"], "ins_paid": f["ins_paid"], "balance": f["balance"]}})
    return {"columns": cols, "rows": rows, "totals": _sum(all_f, ["charges", "ins_paid", "balance"]), "landscape": 1,
            "totals_label": f"Grand Totals    Claim Count: {len(all_f)}"}


PAYMENT_CRIT = [
    {"k": "group_by", "label": "Group By", "type": "select", "options": ["None", "Payer", "Method"], "section": "General"},
    {"k": "pay_date", "label": "Payment Date", "type": "daterange", "section": "Dates"},
    {"k": "payer", "label": "Payer", "type": "select", "options": "payers", "section": "Payment"},
    {"k": "method", "label": "Method", "type": "select", "options": ["CHECK", "EFT", "CASH", "CREDIT CARD", "MONEY ORDER", "OTHER"], "section": "Payment"},
]


def payment_list(cw, crit: dict) -> dict:
    """What came in - EZClaim's staff point people here, not at A/R, for
    "what did we take in"."""
    cols = [{"k": "date", "t": "Date"}, {"k": "name", "t": "From"}, {"k": "method", "t": "Method"}, {"k": "ref", "t": "Check / Ref #"},
            {"k": "amount", "t": "Amount", "m": 1}, {"k": "applied", "t": "Applied", "m": 1}, {"k": "remaining", "t": "Unapplied", "m": 1}]
    ps = []
    for pid, p in cw.records("payment"):
        s = cw.summary("payment", pid, p)
        d = _d(s["date"])
        if not _in(d, *_rng(crit, "pay_date")):
            continue
        who = s["payer"] if s["source"] == "payer" else (s["patient_name"] or "Patient")
        if crit.get("payer") and who != crit["payer"]:
            continue
        if crit.get("method") and s["method"] != crit["method"]:
            continue
        ps.append({"d": d, "who": who, **s})
    ps.sort(key=lambda s: (s["d"] or date.min, s["who"]))
    by = crit.get("group_by") or "None"
    groups: dict = {}
    for s in ps:
        groups.setdefault({"Payer": s["who"], "Method": s["method"] or "(none)"}.get(by, ""), []).append(s)
    rows = []
    keys = ["amount", "applied", "remaining"]
    for g in sorted(groups):
        if by != "None":
            rows.append({"level": 0, "bold": 1, "cells": {"date": g, **_sum(groups[g], keys)}})
        for s in groups[g]:
            rows.append({"level": 1 if by != "None" else 0, "open": {"kind": "payment", "id": s["id"]},
                         "cells": {"date": s["date"], "name": s["who"], "method": s["method"], "ref": s["ref"], **{k: s[k] for k in keys}}})
    return {"columns": cols, "rows": rows, "totals": _sum(ps, keys), "totals_label": f"Grand Totals    Payment Count: {len(ps)}"}


LEDGER_CRIT = [
    {"k": "patient", "label": "Patient", "type": "select", "options": "patients", "section": "Patient"},
    {"k": "dos", "label": "Date of Service", "type": "daterange", "section": "Dates"},
]


def patient_ledger(cw, crit: dict) -> dict:
    """Every charge, payment and adjustment for each patient in date order,
    with a running balance - the page to hand an adjuster or an attorney."""
    cols = [{"k": "date", "t": "Date"}, {"k": "desc", "t": "Description"}, {"k": "code", "t": "Proc"},
            {"k": "charge", "t": "Charges", "m": 1}, {"k": "paid", "t": "Payments", "m": 1}, {"k": "adj", "t": "Adjs", "m": 1},
            {"k": "running", "t": "Balance", "m": 1}]
    want = crit.get("patient")
    per: dict = {}
    for f in claim_facts(cw):
        if want and f["patient"] != want:
            continue
        if not _in(f["first_dos"], *_rng(crit, "dos")):
            continue
        per.setdefault((f["patient"], f["patient_id"]), []).append(f)
    rows, tot = [], {"charge": 0.0, "paid": 0.0, "adj": 0.0}
    for (name, pid), fs in sorted(per.items()):
        rows.append({"level": 0, "bold": 1, "cells": {"date": name}, "open": {"kind": "patient", "id": pid} if pid else None})
        tx = []
        for f in fs:
            for x in f["lines"]:
                tx.append((_d(x["date"]) or date.min, 0, {"date": x["date"], "desc": x["description"] or "Service", "code": x["code"], "charge": x["charge"]}, f["id"]))
                for e in x["entries"]:
                    if e["paid"]:
                        tx.append((_d(e["date"]) or date.min, 1, {"date": e["date"], "desc": "Payment - " + (e["from"] or ""), "paid": e["paid"]}, f["id"]))
                    if e["adj"]:
                        tx.append((_d(e["date"]) or date.min, 2, {"date": e["date"], "desc": "Adjustment " + (e["codes"] or ""), "adj": e["adj"]}, f["id"]))
            manual = cw.money((f["c"].get("tracking") or {}).get("paid_amount"))
            if manual:
                tx.append((_d((f["c"].get("tracking") or {}).get("paid_date")) or date.max, 1,
                           {"date": (f["c"].get("tracking") or {}).get("paid_date", ""), "desc": "Payment (entered on the claim)", "paid": manual}, f["id"]))
        run = 0.0
        for _, _, cells, cid in sorted(tx, key=lambda t: (t[0], t[1])):
            run += cells.get("charge", 0) - cells.get("paid", 0) - cells.get("adj", 0)
            for k in tot:
                tot[k] += cells.get(k, 0)
            rows.append({"level": 1, "open": {"kind": "claim", "id": cid}, "cells": {**cells, "running": round(run, 2)}})
    return {"columns": cols, "rows": rows, "totals": {**{k: round(v, 2) for k, v in tot.items()}, "running": round(tot["charge"] - tot["paid"] - tot["adj"], 2)},
            "totals_label": f"Grand Totals    Patient Count: {len(per)}"}


PATIENT_LIST_CRIT = [
    {"k": "active_only", "label": "Active Patients Only", "type": "check", "section": "Patient"},
    {"k": "payer", "label": "Primary Payer", "type": "select", "options": "payers", "section": "Patient"},
]


def patient_list(cw, crit: dict) -> dict:
    cols = [{"k": "name", "t": "Name"}, {"k": "acct", "t": "Account #"}, {"k": "dob", "t": "DOB"}, {"k": "phone", "t": "Phone"},
            {"k": "payer", "t": "Primary Payer"}, {"k": "insured", "t": "Claim / Insured ID"}, {"k": "doi", "t": "Date of Injury"}]
    rows = []
    for pid, p in sorted(cw.records("patient"), key=lambda x: x[1].get("patient_name", "")):
        if crit.get("active_only") and p.get("active") is False:
            continue
        if crit.get("payer") and p.get("insurer") != crit["payer"]:
            continue
        rows.append({"level": 0, "open": {"kind": "patient", "id": pid},
                     "cells": {"name": p.get("patient_name", ""), "acct": p.get("account_number", ""), "dob": p.get("dob", ""),
                               "phone": p.get("phone", ""), "payer": p.get("insurer", ""), "insured": p.get("claim_number", ""),
                               "doi": p.get("date_of_injury", "")}})
    return {"columns": cols, "rows": rows, "totals": {}, "totals_label": f"Patient Count: {len(rows)}"}


PROC_CRIT = [
    {"k": "dos", "label": "Date of Service", "type": "daterange", "section": "Dates"},
    {"k": "payer", "label": "Claim Primary Payer", "type": "select", "options": "payers", "section": "Claim"},
]


def procedure_code_summary(cw, crit: dict) -> dict:
    cols = [{"k": "code", "t": "Procedure"}, {"k": "desc", "t": "Description"}, {"k": "count", "t": "Count"}, {"k": "units", "t": "Units"},
            {"k": "charges", "t": "Charges", "m": 1}, {"k": "paid", "t": "Payments", "m": 1}, {"k": "adj", "t": "Adjs", "m": 1},
            {"k": "balance", "t": "Balance", "m": 1}]
    agg: dict = {}
    for f in claim_facts(cw):
        if crit.get("payer") and f["payer"] != crit["payer"]:
            continue
        procs = [p for p in f["c"].get("procedures") or [] if (p or {}).get("code")]
        for x, p in zip(f["lines"], procs):
            if not _in(_d(x["date"]), *_rng(crit, "dos")):
                continue
            a = agg.setdefault(x["code"], {"code": x["code"], "desc": x["description"], "count": 0, "units": 0,
                                           "charges": 0.0, "paid": 0.0, "adj": 0.0, "balance": 0.0})
            a["count"] += 1
            a["units"] += int(cw.money(p.get("units")) or 1)
            for k, v in (("charges", x["charge"]), ("paid", x["paid"]), ("adj", x["adj"]), ("balance", x["balance"])):
                a[k] += v
            a["desc"] = a["desc"] or x["description"]
    rows = [{"level": 0, "cells": {**a, "count": str(a["count"]), "units": str(a["units"])}} for _, a in sorted(agg.items())]
    keys = ["charges", "paid", "adj", "balance"]
    return {"columns": cols, "rows": rows, "totals": _sum(list(agg.values()), keys),
            "totals_label": f"Grand Totals    Services: {sum(a['count'] for a in agg.values())}    Units: {sum(a['units'] for a in agg.values())}"}


PROD_CRIT = [{"k": "period", "label": "Date Range", "type": "daterange", "section": "Dates"}]


def production_summary(cw, crit: dict) -> dict:
    """By month: what was charged (by date of service), what came in and what
    was written off (by payment date)."""
    cols = [{"k": "month", "t": "Month"}, {"k": "claims", "t": "Claims"}, {"k": "charges", "t": "Charges", "m": 1},
            {"k": "paid", "t": "Payments", "m": 1}, {"k": "adj", "t": "Adjustments", "m": 1}, {"k": "net", "t": "Charges - Pmts - Adjs", "m": 1}]
    m: dict = {}
    s, e = _rng(crit, "period")

    def bucket(d):
        return m.setdefault(d.strftime("%Y-%m"), {"claims": 0, "charges": 0.0, "paid": 0.0, "adj": 0.0})

    for f in claim_facts(cw):
        if f["first_dos"] and _in(f["first_dos"], s, e):
            b = bucket(f["first_dos"])
            b["claims"] += 1
            b["charges"] += f["charges"]
        tr = f["c"].get("tracking") or {}
        manual, md = cw.money(tr.get("paid_amount")), _d(tr.get("paid_date"))
        if manual and md and _in(md, s, e):  # paid on the claim before Payment Entry existed
            bucket(md)["paid"] += manual
        for x in f["lines"]:
            for en in x["entries"]:
                d = _d(en["date"])
                if d and _in(d, s, e):
                    b = bucket(d)
                    b["paid"] += en["paid"]
                    b["adj"] += en["adj"]
    rows = []
    for k in sorted(m):
        b = m[k]
        rows.append({"level": 0, "cells": {"month": date(int(k[:4]), int(k[5:]), 1).strftime("%B %Y"), "claims": str(b["claims"]),
                                           "charges": round(b["charges"], 2), "paid": round(b["paid"], 2), "adj": round(b["adj"], 2),
                                           "net": round(b["charges"] - b["paid"] - b["adj"], 2)}})
    tot = _sum([r["cells"] for r in rows], ["charges", "paid", "adj", "net"])
    return {"columns": cols, "rows": rows, "totals": tot, "totals_label": "Grand Totals"}


ADJ_CRIT = [
    {"k": "pay_date", "label": "Payment Date", "type": "daterange", "section": "Dates"},
    {"k": "payer", "label": "Claim Primary Payer", "type": "select", "options": "payers", "section": "Claim"},
]


def adjustments(cw, crit: dict) -> dict:
    """Every write-off and reduction with its reason codes - for PIP, mostly
    fee-schedule reductions, which is where underpayments hide."""
    cols = [{"k": "date", "t": "Pmt Date"}, {"k": "name", "t": "Patient"}, {"k": "dos", "t": "DOS"}, {"k": "code", "t": "Proc"},
            {"k": "from", "t": "From"}, {"k": "codes", "t": "Reason Codes"}, {"k": "charge", "t": "Charge", "m": 1},
            {"k": "paid", "t": "Paid", "m": 1}, {"k": "adj", "t": "Adjusted", "m": 1}]
    rows, tot = [], {"charge": 0.0, "paid": 0.0, "adj": 0.0}
    for f in claim_facts(cw):
        if crit.get("payer") and f["payer"] != crit["payer"]:
            continue
        for x in f["lines"]:
            for e in x["entries"]:
                if not e["adj"] or not _in(_d(e["date"]), *_rng(crit, "pay_date")):
                    continue
                rows.append({"level": 0, "open": {"kind": "claim", "id": f["id"]},
                             "cells": {"date": e["date"], "name": f["patient"], "dos": x["date"], "code": x["code"], "from": e["from"],
                                       "codes": e["codes"], "charge": x["charge"], "paid": e["paid"], "adj": e["adj"]}})
                for k in tot:
                    tot[k] += rows[-1]["cells"][k]
    rows.sort(key=lambda r: (_d(r["cells"]["date"]) or date.min))
    return {"columns": cols, "rows": rows, "totals": {k: round(v, 2) for k, v in tot.items()},
            "totals_label": f"Grand Totals    Adjustment Count: {len(rows)}"}


PIP_CRIT = [{"k": "show", "label": "Show", "type": "select", "options": ["Needs action", "Everything with a clock"], "section": "General"}]


def pip_deadlines(cw, crit: dict) -> dict:
    """Ours, not EZClaim's: every Florida PIP clock on one page, worst first."""
    order = {"late": 0, "overdue": 1, "soon": 2, "ok": 3, "": 4}
    cols = [{"k": "name", "t": "Patient"}, {"k": "payer", "t": "Payer"}, {"k": "dos", "t": "1st DOS"}, {"k": "status", "t": "Status"},
            {"k": "clock", "t": "PIP Clock"}, {"k": "next", "t": "Next Deadline"}, {"k": "why", "t": "Why"}, {"k": "balance", "t": "Balance", "m": 1}]
    fs = []
    for f in claim_facts(cw):
        p = f["pip"]
        if not p.get("applies") or f["billing"] == "paid":
            continue
        if (crit.get("show") or "Needs action") == "Needs action" and p["level"] not in ("late", "overdue", "soon"):
            continue
        if not (p["items"] or p["flags"]):
            continue
        fs.append(f)
    fs.sort(key=lambda f: (order.get(f["pip"]["level"], 9), f["patient"]))
    rows = []
    for f in fs:
        p = f["pip"]
        nxt = min(p["items"], key=lambda i: i["days"]) if p["items"] else None
        rows.append({"level": 0, "open": {"kind": "claim", "id": f["id"]},
                     "cells": {"name": f["patient"], "payer": f["payer"], "dos": _mdy(f["first_dos"]), "status": f["status"],
                               "clock": p["text"], "next": f"{nxt['label']} {nxt['date']}" if nxt else "",
                               "why": (p["flags"][0]["text"] if p["flags"] else "")[:90], "balance": f["balance"]}})
    return {"columns": cols, "rows": rows, "totals": _sum(fs, ["balance"]), "landscape": 1,
            "totals_label": f"Claims: {len(fs)}"}


REPORTS = {
    "Accounts Receivable": (accounts_receivable, AR_CRIT,
                            "AR report showing the outstanding balances to payers as of the given aging date."),
    "Adjustments": (adjustments, ADJ_CRIT, "Every write-off and reduction, with its reason codes."),
    "Claim List": (claim_list, CLAIM_LIST_CRIT,
                   "Shows patient name, invoice #, diagnosis, dates, payments and balance - with totals. The one to use for receivables."),
    "Insurance Follow-Up": (insurance_followup, FOLLOWUP_CRIT,
                            "Shows what's outstanding with each payer, oldest first, with the PIP clock. Useful for claim follow-up."),
    "Patient Ledger": (patient_ledger, LEDGER_CRIT,
                       "Every charge, payment and adjustment for a patient, in date order, with a running balance."),
    "Patient List": (patient_list, PATIENT_LIST_CRIT, "Patient name, account #, DOB, phone, primary payer and claim #."),
    "Payment List": (payment_list, PAYMENT_CRIT, "Payments received, by date, with how much of each was applied."),
    "PIP Deadlines": (pip_deadlines, PIP_CRIT,
                      "Florida PIP: claims to bill, carriers overdue, demand letters due - worst first. (Thunder's own report.)"),
    "Procedure Code Summary": (procedure_code_summary, PROC_CRIT, "Count, units, charges and payments by procedure code."),
    "Production Summary": (production_summary, PROD_CRIT, "Charges, payments and adjustments by month."),
}


def catalogue(cw) -> dict:
    """The report list and the choices the criteria dropdowns offer."""
    payers = sorted({str(c.get("insurer") or "") for _, c in cw.records("claim") if c.get("insurer")}
                    | {str(p.get("name") or "") for _, p in cw.records("payer") if p.get("name")})
    provs = sorted({str(c.get("treating_provider") or "") for _, c in cw.records("claim") if c.get("treating_provider")})
    pats = sorted({str(p.get("patient_name") or "") for _, p in cw.records("patient") if p.get("patient_name")}
                  | {str(c.get("patient_name") or "") for _, c in cw.records("claim") if c.get("patient_name")})
    return {"reports": [{"name": n, "description": r[2], "criteria": r[1]} for n, r in REPORTS.items()],
            "options": {"payers": payers, "providers": provs, "patients": pats}}


def run(cw, name: str, crit: dict) -> dict:
    if name not in REPORTS:
        raise ValueError("unknown report")
    fn, spec, _ = REPORTS[name]
    crit = {k: v for k, v in (crit or {}).items() if v not in (None, "")}
    for c in spec:  # defaults, so the echo line says what was actually used
        if c["k"] not in crit:
            if c["type"] == "date":
                crit[c["k"]] = date.today().strftime("%m/%d/%Y")
            elif c["k"] in ("group_by", "show"):
                crit[c["k"]] = c["options"][0]
    out = fn(cw, crit)
    out.setdefault("landscape", 0)
    st = cw.get_settings()["statement"]
    out.update(title=name, echo=_echo(spec, crit), run_at=date.today().strftime("%m/%d/%Y"),
               practice=[x for x in (st.get("return_name"), st.get("return_addr1"), st.get("return_addr2"),
                                     ", ".join(filter(None, [st.get("return_city"), " ".join(filter(None, [st.get("return_state"), st.get("return_zip")]))])),
                                     st.get("return_phone")) if x])
    return out
