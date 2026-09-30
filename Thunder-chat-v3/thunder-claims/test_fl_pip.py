#!/usr/bin/env python3
"""Florida PIP deadline checks (Fla. Stat. 627.736), on fixed dates.

    python3 test_fl_pip.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fl_pip  # noqa: E402

PASSED = FAILED = 0
TODAY = date(2026, 3, 1)


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  pass  {name}")
    else:
        FAILED += 1
        print(f"  FAIL  {name}  {detail}")


def claim(**kw):
    c = {"date_of_injury": "02/01/2026", "accident_state": "FL",
         "procedures": [{"code": "98941", "date": "02/05/2026", "charge": "100"}],
         "tracking": {"billing": "draft"}}
    tr = kw.pop("tracking", {})
    c.update(kw)
    c["tracking"].update(tr)
    return c


def item(r, key):
    return next((i for i in r["items"] if i["key"] == key), None)


print("filing window")
r = fl_pip.deadlines(claim(), TODAY)
f = item(r, "file")
check("unbilled: postmark by = oldest service + 35 days", f and f["date"] == "03/12/2026" and f["days"] == 11, f)
check("grid text counts down", r["text"] == "Bill in 11d", r["text"])
r = fl_pip.deadlines(claim(), date(2026, 3, 8))
check("within 7 days is 'soon'", item(r, "file")["level"] == "soon")
r = fl_pip.deadlines(claim(), date(2026, 3, 20))
check("past 35 days is late, and says it can't be billed", r["level"] == "late" and r["text"] == "Late 8d"
      and any("can no longer be billed" in x["text"] for x in r["flags"]), r)
r = fl_pip.deadlines(claim(pip_notice_sent="02/20/2026"), date(2026, 3, 20))
check("notice within 21 days of first treatment -> 75 days", r["window"] == 75 and item(r, "file")["date"] == "04/21/2026", r)
r = fl_pip.deadlines(claim(pip_notice_sent="03/01/2026"), TODAY)
check("notice after 21 days does not extend, and is flagged", r["window"] == 35
      and any("35-day limit applies" in x["text"] for x in r["flags"]), r)
r = fl_pip.deadlines(claim(), TODAY)
n = item(r, "notice")
check("no notice reminder once the 21 days have gone", n is None, n)
r = fl_pip.deadlines(claim(), date(2026, 2, 10))
n = item(r, "notice")
check("notice reminder = first treatment + 21 days", n and n["date"] == "02/26/2026", n)
c = claim(tracking={"billing": "sent", "sent_date": "03/15/2026"})
c["procedures"].append({"code": "97140", "date": "02/20/2026", "charge": "40"})
r = fl_pip.deadlines(c, date(2026, 3, 16))
check("billed late: names the lines past the window", any("1 service date(s) from 02/05/2026" in x["text"] for x in r["flags"]), r["flags"])

print("14-day initial care")
r = fl_pip.deadlines(claim(procedures=[{"code": "98941", "date": "02/20/2026"}]), TODAY)
check("first treatment 19 days after the accident is flagged", any("19 days after the accident" in x["text"] for x in r["flags"]), r["flags"])
r = fl_pip.deadlines(claim(first_treatment="02/10/2026", procedures=[{"code": "98941", "date": "02/20/2026"}]), TODAY)
check("an earlier first treatment on another claim counts", not any("after the accident" in x["text"] for x in r["flags"]), r["flags"])
r = fl_pip.deadlines(claim(date_of_injury=""), TODAY)
check("no date of injury is called out", any("No date of injury" in x["text"] for x in r["flags"]))
r = fl_pip.deadlines(claim(procedures=[{"code": "98941", "date": "02/20/2026"}], tracking={"billing": "paid", "sent_date": "02/25/2026"}), TODAY)
check("grid says why when there is no clock to show", r["text"] == "Care >14d", r["text"])

print("carrier payment clock")
sent = claim(tracking={"billing": "sent", "sent_date": "02/10/2026"})
r = fl_pip.deadlines(sent, TODAY)
p = item(r, "pay")
check("sent: due 30 days from the bill date, marked as estimated", p and p["date"] == "03/12/2026" and "received date" in p["note"], p)
r = fl_pip.deadlines(claim(tracking={"billing": "sent", "sent_date": "02/10/2026", "received_date": "02/14/2026"}), TODAY)
check("received date gives the exact day", item(r, "pay")["date"] == "03/16/2026")
r = fl_pip.deadlines(sent, date(2026, 3, 20))
check("overdue after 30 days, and says a demand letter may go", r["level"] == "overdue" and r["text"] == "Overdue 8d"
      and any("demand letter" in x["text"] for x in r["flags"]), r)
r = fl_pip.deadlines(claim(tracking={"billing": "sent", "sent_date": "02/10/2026", "fraud_notice": "03/01/2026"}), date(2026, 3, 20))
check("under investigation: 90 days, not overdue yet", item(r, "pay")["date"] == "05/11/2026" and r["level"] == "ok", r)
r = fl_pip.deadlines(claim(tracking={"billing": "paid", "sent_date": "02/10/2026"}), date(2026, 6, 1))
r = fl_pip.deadlines(claim(tracking={"billing": "sent"}), TODAY)
check("submitted with no bill date is flagged, not silently skipped", any(f["key"] == "no_sent" for f in r["flags"]), r["flags"])
check("a paid claim has no clock", item(r, "pay") is None and r["level"] != "overdue")

print("scope")
r = fl_pip.deadlines(claim(accident_state="GA"), TODAY)
check("another state's accident is not held to Florida's rules", r["applies"] is False and r["level"] == "")
r = fl_pip.deadlines(claim(accident_state=""), TODAY)
check("a blank state is treated as Florida (the office bills only FL PIP)", r["applies"] is True)

print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
