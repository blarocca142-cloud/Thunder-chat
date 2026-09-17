"""What Thunder would tell Blayne if he walked in and asked "anything I should know?"

Everything here already existed somewhere: fleet health on Odris, memory
proposals waiting for approval, the claims review queue, canary alerts, the app
version. All of it sitting behind an endpoint nobody opens. A system that only
answers when asked is a system whose warnings arrive late.

Two rules, learned from the health work:

**Silence when nothing is wrong.** A digest that says something every day
becomes something you stop reading, and then the one that mattered goes past
unread too. If nothing needs a person, it says so in one line and stops.

**Never invent urgency.** Each item carries the evidence it came from. "Drive
sda is 6.4 years old and carries /" is a fact he can act on; "system health
degraded" is noise wearing a suit.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ODRIS_HEALTH = "http://10.168.168.15:9007/fleet/health"


def _get(url: str, timeout: int = 10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def item(kind: str, headline: str, detail: str, action: str = "",
         severity: str = "info") -> dict:
    return {"kind": kind, "headline": headline, "detail": detail,
            "action": action, "severity": severity}


def hardware() -> list[dict]:
    health = _get(ODRIS_HEALTH, timeout=12)
    if not health:
        return [item("hardware", "No hardware report",
                     "Odris has not answered on port 9007, so nothing is being "
                     "watched right now.",
                     "Check that thunder-health is running on odris.", "warning")]
    out = []
    for node in health.get("nodes", []):
        for comp in node.get("components", []):
            for f in comp.get("findings", []):
                if f.get("severity") not in ("attention", "watch"):
                    continue
                out.append(item(
                    "hardware",
                    f"{node['host']}: {f['finding']}",
                    f["why"],
                    f["fix"],
                    "critical" if f["severity"] == "attention" else "warning"))
    return out


def claims(vault_dir: Path) -> list[dict]:
    queue = vault_dir / "review_queue.json"
    if not queue.is_file():
        return []
    try:
        items = json.loads(queue.read_text())["items"]
    except Exception:
        return []
    blocked = [i for i in items if i.get("status") == "BLOCK"]
    review = [i for i in items if i.get("status") == "REVIEW"]
    failed = [i for i in items if i.get("status") == "FAILED"]
    out = []
    if blocked:
        out.append(item(
            "claims", f"{len(blocked)} claims cannot be billed",
            "Each has a mechanical error - a bad check digit, a malformed code "
            "or an impossible date. They will be rejected if sent.",
            "./review.py to see which, and why.", "critical"))
    if review:
        out.append(item(
            "claims", f"{len(review)} claims waiting to be read",
            "These passed every mechanical check, but something was repaired or "
            "is missing, so a person signs off before they go anywhere.",
            "./review.py", "warning"))
    if failed:
        out.append(item(
            "claims", f"{len(failed)} scans could not be read at all",
            "OCR returned nothing. Usually a blank page, a sideways scan, or a "
            "photograph too dark to read.",
            "Re-scan those pages.", "warning"))
    return out


def memory_waiting(memory_dir: Path) -> list[dict]:
    pending = memory_dir / "pending.json"
    if not pending.is_file():
        return []
    try:
        items = json.loads(pending.read_text())
    except Exception:
        return []
    if not items:
        return []
    conflicts = [i for i in items if i.get("conflict")]
    detail = (f"Thunder read yesterday's conversations and picked out "
              f"{len(items)} things it thinks are worth remembering. None are "
              f"in memory until approved.")
    if conflicts:
        detail += (f" {len(conflicts)} of them contradict each other, so at "
                   f"least one is wrong.")
    return [item("memory", f"{len(items)} things Thunder wants to remember",
                 detail, "GET /memory/pending, then approve or reject", "info")]


def security(data_dir: Path) -> list[dict]:
    out = []
    alerts = data_dir / "canary_alerts.log"
    if alerts.is_file():
        # Only recent hits. Counting every line ever logged means one old
        # access nags forever, and a warning that never clears is one that
        # stops being read - which defeats the point of having it.
        cutoff = datetime.now(timezone.utc).timestamp() - 7 * 86400
        recent = []
        try:
            for line in alerts.read_text().splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                when = datetime.fromisoformat(rec["at"]).timestamp()
                if when >= cutoff:
                    recent.append(rec)
        except Exception:
            recent = []
        if recent:
            newest = max(r["at"] for r in recent)[:19].replace("T", " ")
            files = sorted({r["file"] for r in recent})
            out.append(item(
                "security",
                f"{len(recent)} honeyfile accesses in the last 7 days",
                f"Something opened a decoy file - most recently {newest}, "
                f"touching {', '.join(f.split('/')[-1] for f in files[:3])}. "
                f"Nothing legitimate ever reads these.",
                "Read thunder-data/canary_alerts.log. If this was you testing, "
                "clear the log and it stops reporting.",
                "critical"))
    return out


def build(data_dir: Path, vault_dir: Path, app_version: str | None = None,
          latest_version: str | None = None) -> dict:
    items: list[dict] = []
    items += security(data_dir)          # first: it is the only one that means intrusion
    items += hardware()
    items += claims(vault_dir)
    items += memory_waiting(data_dir / "memory")

    if app_version and latest_version and app_version != latest_version:
        items.append(item("app", f"App update available ({latest_version})",
                          f"The phone is on {app_version}.",
                          "Open Settings in the app to install it.", "info"))

    order = {"critical": 0, "warning": 1, "info": 2}
    items.sort(key=lambda i: order.get(i["severity"], 3))
    critical = sum(1 for i in items if i["severity"] == "critical")
    warning = sum(1 for i in items if i["severity"] == "warning")

    if not items:
        spoken = "Nothing needs you. The fleet is healthy, no claims are waiting."
    else:
        parts = []
        if critical:
            parts.append(f"{critical} thing{'s' if critical > 1 else ''} needing attention")
        if warning:
            parts.append(f"{warning} to look at")
        rest = len(items) - critical - warning
        if rest:
            parts.append(f"{rest} for information")
        # The top item is spoken in full - a count alone tells him to go
        # looking, which is the thing this is supposed to save him.
        spoken = " and ".join(parts).capitalize() + ". " + items[0]["headline"] + "."

    return {
        "at": datetime.now(timezone.utc).isoformat(),
        "quiet": not items,
        "critical": critical,
        "warning": warning,
        "items": items,
        "spoken": spoken,
    }
