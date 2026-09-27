#!/usr/bin/env python3
"""Checks for alerts.py, aimed at the behaviours that made the phone lie.

The bug being fixed is a lifecycle bug, so most of these are lifecycle: a
finding appears, sticks around while it is still true, survives a wording
change, clears when it goes away, and is still readable afterwards. Run:

    python3 test_alerts.py
"""
import json
import shutil
import tempfile
from pathlib import Path

import alerts

PASS, FAIL = 0, 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok    {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{('  -> ' + extra) if extra else ''}")


def item(kind, headline, severity="warning", detail="d", action="a"):
    return {"kind": kind, "headline": headline, "detail": detail,
            "action": action, "severity": severity}


DRIVE = item("hardware", "serverus: /dev/sda has 6.4 years of runtime carrying /boot, /")
CLAIMS4 = item("claims", "4 claims waiting to be read")
CLAIMS5 = item("claims", "5 claims waiting to be read")
CANARY = item("security", "2 honeyfile accesses in the last 7 days", "critical")


def main():
    d = Path(tempfile.mkdtemp(prefix="alerts_test_"))
    try:
        print("\nfirst sighting")
        active = alerts.record(d, [DRIVE, CLAIMS4])
        check("both findings become active", len(active) == 2, str(len(active)))
        check("history file written", (d / "alert_history.json").is_file())
        first = {a["headline"]: a for a in active}
        drive_id = next(a["id"] for a in active if a["kind"] == "hardware")
        check("first_seen set", all(a["first_seen"] for a in active))
        check("not resolved", all(a["resolved_at"] is None for a in active))

        print("\nstill true on the next poll")
        prev_first_seen = first[DRIVE["headline"]]["first_seen"]
        active = alerts.record(d, [DRIVE, CLAIMS4])
        check("no duplicate entry", len(active) == 2, str(len(active)))
        drive = next(a for a in active if a["id"] == drive_id)
        check("first_seen does not move", drive["first_seen"] == prev_first_seen)
        check("seen_count climbs", drive["seen_count"] == 2, str(drive["seen_count"]))

        print("\nthe count in the headline changes")
        active = alerts.record(d, [DRIVE, CLAIMS5])
        check("count change is the SAME alert, not a new one",
              len(active) == 2, str(len(active)))
        claims = next(a for a in active if a["kind"] == "claims")
        check("latest wording is stored", "5 claims" in claims["headline"],
              claims["headline"])
        check("still the original first_seen",
              claims["first_seen"] == first[CLAIMS4["headline"]]["first_seen"])

        print("\nthe drive finding goes away")
        active = alerts.record(d, [CLAIMS5])
        check("resolved findings leave the active list", len(active) == 1,
              str(len(active)))
        rows = alerts.history(d)
        check("but are still readable in history", len(rows) == 2, str(len(rows)))
        gone = next(r for r in rows if r["id"] == drive_id)
        check("resolved_at is stamped", bool(gone["resolved_at"]))
        check("active sorts above resolved", rows[0]["resolved_at"] is None)

        print("\nand comes back")
        active = alerts.record(d, [DRIVE, CLAIMS5])
        back = next(a for a in active if a["id"] == drive_id)
        check("reopened", back["resolved_at"] is None)
        check("return is recorded", bool(back["returned_at"]))
        check("first_seen STILL the original", back["first_seen"] == prev_first_seen)

        print("\nacknowledging")
        alerts.ack(d, drive_id)
        rows = alerts.history(d, include_resolved=False)
        acked = next(r for r in rows if r["id"] == drive_id)
        check("acked_at set", bool(acked["acked_at"]))
        check("ack does NOT remove it from active", acked["resolved_at"] is None)
        check("ack of an unknown id returns None", alerts.ack(d, "nope") is None)
        c = alerts.counts(d)
        check("counts: 2 active", c["active"] == 2, json.dumps(c))
        check("counts: 1 unacked", c["unacked"] == 1, json.dumps(c))

        print("\nack clears when the finding returns")
        alerts.record(d, [CLAIMS5])           # drive resolves
        alerts.record(d, [DRIVE, CLAIMS5])    # and returns
        rows = alerts.history(d, include_resolved=False)
        again = next(r for r in rows if r["id"] == drive_id)
        check("a returning finding is unacknowledged again",
              again["acked_at"] is None)

        print("\nseverity ordering and model context")
        alerts.record(d, [DRIVE, CLAIMS5, CANARY])
        rows = alerts.history(d, include_resolved=False)
        check("critical sorts first", rows[0]["severity"] == "critical",
              rows[0]["severity"])
        block = alerts.context_block(d)
        check("context names the actual drive", "/dev/sda" in block)
        check("context carries the action", "what to do" in block)
        check("context is labelled authoritative", "authoritative" in block)
        check("context tells the model where notifications came from",
              "notification" in block.lower())

        print("\nempty and broken states")
        empty = Path(tempfile.mkdtemp(prefix="alerts_empty_"))
        try:
            check("no history means no active alerts",
                  alerts.history(empty) == [])
            check("no history means empty context",
                  alerts.context_block(empty) == "")
            check("quiet digest resolves everything",
                  alerts.record(empty, []) == [])
            (empty / "alert_history.json").write_text("{not json at all")
            check("corrupt history does not raise", alerts.history(empty) == [])
            check("corrupt history still accepts a write",
                  len(alerts.record(empty, [DRIVE])) == 1)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

        print("\npruning")
        many = Path(tempfile.mkdtemp(prefix="alerts_prune_"))
        try:
            alerts.record(many, [item("hardware", f"finding number {i}")
                                 for i in range(alerts.MAX_ENTRIES + 40)])
            stored = json.loads((many / "alert_history.json").read_text())["alerts"]
            check("never exceeds the cap",
                  len(stored) <= alerts.MAX_ENTRIES, str(len(stored)))
        finally:
            shutil.rmtree(many, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n{PASS} passed, {FAIL} failed\n")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
