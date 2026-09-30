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

print("benefits limit")
b = fl_pip.benefits({"emc": "yes"}, 3000, 1000)
check("EMC: $10,000 limit, used and left", b["limit"] == 10000 and b["remaining"] == 7000 and b["expected"] == 800 and not b["flags"], b)
b = fl_pip.benefits({"emc": "no"}, 2000, 1000)
check("no EMC: $2,500, and open bills worth more than what is left are flagged", b["limit"] == 2500 and b["remaining"] == 500
      and any(f["key"] == "short" for f in b["flags"]), b)
b = fl_pip.benefits({"emc": "yes", "pip_paid_others": "9,500"}, 600, 0)
check("what the carrier paid other providers counts against the limit", b["remaining"] == -100 and b["level"] == "late"
      and any(f["key"] == "exhausted" for f in b["flags"]), b)
b = fl_pip.benefits({}, 2000, 1000)
check("EMC not on file: limit unknown, and past $2,500 is called out", b["limit"] is None and b["remaining"] is None
      and {f["key"] for f in b["flags"]} == {"no_emc", "emc_needed"}, b)
b = fl_pip.benefits({"pip_limit": "5000"}, 1000, 0)
check("a policy-specific limit overrides the statute's", b["limit"] == 5000 and b["remaining"] == 4000, b)

print("denials and demand letters")
den = claim(tracking={"billing": "denied", "sent_date": "02/10/2026", "denial_code": "ime"})
r = fl_pip.deadlines(den, TODAY)
check("a denial names its type and the next step", any(f["key"] == "denial" and "IME cut-off" in f["text"] for f in r["flags"]), r["flags"])
check("before day 30 a demand letter is not allowed, and says when it will be",
      r["demand_ok"] is False and r["demand_from"] == "03/13/2026" and item(r, "demand_wait"), r)
r = fl_pip.deadlines(den, date(2026, 3, 13))
check("the day after the claim is overdue, a demand letter is allowed", r["demand_ok"] is True)
r = fl_pip.deadlines(claim(tracking={"billing": "sent", "sent_date": "02/10/2026", "fraud_notice": "02/20/2026"}), date(2026, 4, 1))
check("an investigation pushes the demand letter out to day 90", r["demand_ok"] is False and r["demand_from"] == "05/12/2026", r["demand_from"])
check("no bill date, no demand letter", fl_pip.deadlines(claim(tracking={"billing": "denied"}), date(2026, 9, 1))["demand_ok"] is False)
dem = claim(tracking={"billing": "sent", "sent_date": "01/02/2026", "demand_sent": "02/10/2026"})
r = fl_pip.deadlines(dem, TODAY)
a = item(r, "demand")
check("demand sent: 30 days from an estimated delivery, until the green card is in", a and a["date"] == "03/17/2026" and "green card" in a["note"], a)
check("once the demand is out, the plain 'overdue' nag stops", item(r, "pay") is None and r["text"] == "Demand 16d", r["text"])
dem["tracking"]["demand_received"] = "02/13/2026"
r = fl_pip.deadlines(dem, date(2026, 3, 20))
check("green card date gives the exact day, then says take it to the attorney", item(r, "demand")["date"] == "03/15/2026"
      and r["text"] == "Demand expired" and any(f["key"] == "demand_expired" for f in r["flags"]), r)
dem["tracking"]["billing"] = "paid"
check("a paid claim drops the demand clock", item(fl_pip.deadlines(dem, date(2026, 3, 20)), "demand") is None)

print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
