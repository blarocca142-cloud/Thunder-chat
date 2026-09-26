"""Alert history: the thing a notification can actually be opened onto.

The digest was always computed live and thrown away. That is fine for "anything
I should know?" and useless for the thing that actually happens: the phone
buzzes at 3pm, Blayne opens the app at 9pm, and by then the digest has been
recomputed - so either the finding has cleared and there is nothing to see, or
it is still there but no screen ever displayed it. Both feel identical from the
outside, and both feel like the notification lied.

So the digest now leaves a trail. Every time it is built - which already happens
on every poll, no new timer needed - the items are folded into a history on
disk. A finding gets one entry with a `first_seen`, a `last_seen` that keeps
moving while it is still true, and a `resolved_at` the moment it stops
appearing. Nothing is deleted just because the condition went away, because
"it cleared on its own at 4am" is exactly the kind of thing worth being able to
read the next morning.

Two decisions worth keeping:

**Identity ignores numbers.** "4 claims waiting to be read" and "5 claims
waiting to be read" are one ongoing situation, not two alerts, so the key is
built with the digits masked out. Otherwise every count change orphans the old
entry and re-notifies as if it were new, which is how an alert feed teaches you
to ignore it. The stored headline is always the latest wording.

**Resolved is recorded, not erased.** A finding that fixes itself still gets to
be history. Only age prunes anything, and only after the entry has been
resolved for a month.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

# How long a resolved alert stays readable, and a hard cap so a flapping
# finding can never grow the file without bound.
KEEP_RESOLVED_DAYS = 30
MAX_ENTRIES = 300

_lock = threading.Lock()

_DIGITS = re.compile(r"\d+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key(item: dict) -> str:
    """Stable id for a finding, insensitive to the numbers inside it.

    The headline carries live values - a drive's age in years, a count of
    waiting claims - and those move on their own. Keying on the raw text makes
    every tick a brand new alert; masking the digits keeps one entry for one
    situation.
    """
    subject = _DIGITS.sub("#", f"{item.get('kind','')}|{item.get('headline','')}".lower())
    return hashlib.sha1(subject.encode()).hexdigest()[:12]


def _path(data_dir: Path) -> Path:
    return data_dir / "alert_history.json"


def _load(data_dir: Path) -> dict:
    p = _path(data_dir)
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text())
    except Exception:
        # A corrupt history must never take the digest down with it. Losing the
        # trail is bad; failing /digest and /status is worse.
        return {}
    return raw.get("alerts", {}) if isinstance(raw, dict) else {}


def _save(data_dir: Path, alerts: dict) -> None:
    p = _path(data_dir)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps({"alerts": alerts}, indent=2))
    os.replace(tmp, p)  # atomic: a reader never sees a half-written file


def _local(iso: str | None) -> str:
    """Render a stored UTC timestamp in Blayne's own timezone.

    Everything on disk is UTC, deliberately. Everything shown to a person is
    local, also deliberately: a canary hit logged at 07:12 UTC was 03:12 in the
    kitchen, and quoting the raw value turned "me, last night" into "a stranger,
    this morning" and cost an hour of forensics.
    """
    if not iso:
        return "unknown"
    try:
        return (datetime.fromisoformat(iso).astimezone()
                .strftime("%a %d %b, %I:%M %p %Z"))
    except Exception:
        return iso


def _age_days(iso: str) -> float:
    try:
        return (datetime.now(timezone.utc)
                - datetime.fromisoformat(iso)).total_seconds() / 86400
    except Exception:
        return 0.0


def _prune(alerts: dict) -> dict:
    keep = {
        k: v for k, v in alerts.items()
        if not v.get("resolved_at") or _age_days(v["resolved_at"]) < KEEP_RESOLVED_DAYS
    }
    if len(keep) > MAX_ENTRIES:
        # Oldest activity goes first, and an active finding always outranks a
        # resolved one regardless of age.
        ordered = sorted(keep.items(),
                         key=lambda kv: (bool(kv[1].get("resolved_at")),
                                         kv[1].get("last_seen", "")),
                         reverse=True)
        keep = dict(ordered[:MAX_ENTRIES])
    return keep


def record(data_dir: Path, items: list[dict]) -> list[dict]:
    """Fold a freshly built digest into the history. Returns the active list.

    Called from /digest, so the app's existing six-hourly poll is what
    maintains this. No extra timer, and the history stays honest about when a
    finding was actually observed rather than when someone happened to look.
    """
    now = _now()
    seen: set[str] = set()
    with _lock:
        alerts = _load(data_dir)
        for it in items:
            k = _key(it)
            seen.add(k)
            existing = alerts.get(k)
            if existing:
                # Same situation, still true. Latest wording wins; first_seen
                # never moves - that is the whole value of the entry.
                existing.update({
                    "headline": it.get("headline", ""),
                    "detail": it.get("detail", ""),
                    "action": it.get("action", ""),
                    "severity": it.get("severity", "info"),
                    "last_seen": now,
                    "seen_count": existing.get("seen_count", 1) + 1,
                })
                if existing.get("resolved_at"):
                    # It came back. Keep the history of the first sighting but
                    # reopen it, and say plainly that it returned.
                    existing["returned_at"] = now
                    existing["resolved_at"] = None
                    existing["acked_at"] = None
            else:
                alerts[k] = {
                    "id": k,
                    "kind": it.get("kind", ""),
                    "headline": it.get("headline", ""),
                    "detail": it.get("detail", ""),
                    "action": it.get("action", ""),
                    "severity": it.get("severity", "info"),
                    "first_seen": now,
                    "last_seen": now,
                    "seen_count": 1,
                    "resolved_at": None,
                    "returned_at": None,
                    "acked_at": None,
                }
        for k, v in alerts.items():
            if k not in seen and not v.get("resolved_at"):
                v["resolved_at"] = now
        alerts = _prune(alerts)
        _save(data_dir, alerts)
        return [v for v in alerts.values() if not v.get("resolved_at")]


def history(data_dir: Path, limit: int = 50,
            include_resolved: bool = True) -> list[dict]:
    """Newest activity first, active findings always above resolved ones."""
    with _lock:
        alerts = _load(data_dir)
    rows = list(alerts.values())
    if not include_resolved:
        rows = [r for r in rows if not r.get("resolved_at")]
    # Two passes rather than one clever key: Python's sort is stable, so newest
    # first survives the second sort within each severity band.
    order = {"critical": 0, "warning": 1, "info": 2}
    rows.sort(key=lambda r: r.get("last_seen", ""), reverse=True)
    rows.sort(key=lambda r: (bool(r.get("resolved_at")),
                             order.get(r.get("severity"), 3)))
    return rows[:limit]


def ack(data_dir: Path, alert_id: str) -> dict | None:
    """Mark a finding as read. It stays in the list - acknowledging a 6-year-old
    drive does not make it younger - but the app can stop shouting about it."""
    with _lock:
        alerts = _load(data_dir)
        row = alerts.get(alert_id)
        if not row:
            return None
        row["acked_at"] = _now()
        _save(data_dir, alerts)
        return row


def counts(data_dir: Path) -> dict:
    active = history(data_dir, limit=MAX_ENTRIES, include_resolved=False)
    return {
        "active": len(active),
        "critical": sum(1 for a in active if a.get("severity") == "critical"),
        "warning": sum(1 for a in active if a.get("severity") == "warning"),
        "unacked": sum(1 for a in active if not a.get("acked_at")),
    }


def context_block(data_dir: Path, limit: int = 8) -> str:
    """What to hand a model so it can answer "what's wrong with serverus?".

    This is the other half of the bug. The digest knew about the drive and the
    chat model did not, so asking Thunder about the notification it had just
    sent got a blank look. Findings are labelled as live readings rather than
    background prose, because retrieval that is merely present gets ignored in
    favour of the training prior.
    """
    active = history(data_dir, limit=limit, include_resolved=False)
    if not active:
        return ""
    lines = ["LIVE SYSTEM ALERTS (current readings from this machine and the "
             "fleet - authoritative, prefer these over anything you recall):"]
    for a in active:
        since = _local(a.get("first_seen"))
        lines.append(
            f"- [{a.get('severity','info').upper()}] {a.get('headline','')}"
            f" (first seen {since})\n"
            f"  why it matters: {a.get('detail','')}\n"
            f"  what to do: {a.get('action','') or 'nothing yet'}")
    lines.append("If Blayne asks what a notification was about, it was one of "
                 "the above. Answer from these, and say plainly if none match.")
    return "\n".join(lines)
