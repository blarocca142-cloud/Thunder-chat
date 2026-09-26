"""Odris, reachable from the phone.

Odris has been a genuinely separate assistant for a while - its own system
prompt, its own context of live system readings rather than chat history - but
it only ever existed inside the admin dashboard on odris:9005, behind a password
in a browser. So the assistant whose entire job is explaining what broke was the
one you could not reach from the couch, which is where you are when the phone
buzzes.

This is that same assistant, served by Main so the app can talk to it. Both
personas run on Main's GPU regardless; the GPU is the only one in the fleet.
What makes Odris a different assistant is the prompt and the context, and those
are what this module carries.

Three deliberate differences from Thunder:

**It reads hardware findings.** The dashboard's own snapshot never included
`/fleet/health`, which is why Odris could say "serverus is up" while the digest
was warning about serverus's boot drive. Both were right and neither was useful.
Health findings and the alert history are in the context here.

**It does not write to Thunder's memory.** Odris keeps a short scrollback of its
own so a conversation works, and nothing it says reaches the nightly
consolidator. An ops assistant narrating the fleet into long-term memory would
poison the well with transient facts - "serverus is down" is true for four
minutes and wrong forever after.

**It is read-only here.** The dashboard's `parse_and_execute_command` can
approve, apply and start maintenance, gated behind the dashboard password and
the admin secret. None of that is exposed through this path, because Main's own
auth defaults to off - an unauthenticated LAN endpoint that can deploy code is
not a trade worth making for convenience. Ask Odris what to do; do it from the
dashboard.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

SYSTEM_PROMPT = (
    "You are Odris, Blayne's ops assistant for the Thunder AI fleet. You are "
    "NOT Thunder (the user-facing chat AI) - you are the separate assistant "
    "that watches the machines: node health, hardware findings, alerts, jobs "
    "and errors. Talk like a sharp sysadmin friend, direct and short, never a "
    "corporate status report.\n\n"
    "You get a live snapshot below. It is authoritative - prefer it over "
    "anything you think you remember about this fleet, and never invent a "
    "reading you were not given. If the snapshot does not cover what he asked, "
    "say so plainly and say which service would know.\n\n"
    "When he asks what a notification was about, the answer is in the ALERTS "
    "section. Name the specific finding, say when it started, say whether it is "
    "still happening, and say what it actually means for him - not the severity "
    "label. Distinguish 'this needs you today' from 'this is worth knowing'. "
    "An old disk that is still healthy is not an emergency, and saying so is "
    "more useful than sounding alarmed.\n\n"
    "You cannot change anything from here - this path is read-only. If "
    "something needs approving, applying or maintenance mode, tell him to use "
    "the Odris dashboard on port 9005 and say which command to give it."
)

# Its own scrollback, kept small and kept away from Thunder's memory.
HISTORY_TURNS = 12


def _hist_path(data_dir: Path) -> Path:
    return data_dir / "odris_chat.json"


def load_history(data_dir: Path) -> list[dict]:
    p = _hist_path(data_dir)
    if not p.is_file():
        return []
    try:
        rows = json.loads(p.read_text())
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def append_history(data_dir: Path, question: str, reply: str) -> None:
    rows = load_history(data_dir)
    rows.append({"at": datetime.now(timezone.utc).isoformat(),
                 "role": "user", "content": question})
    rows.append({"at": datetime.now(timezone.utc).isoformat(),
                 "role": "assistant", "content": reply})
    rows = rows[-HISTORY_TURNS * 2:]
    p = _hist_path(data_dir)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, indent=2))
    os.replace(tmp, p)


def _findings(health: dict, min_severity=("attention", "watch")) -> list[str]:
    """The hardware findings worth a sentence. `info` findings are mostly
    "this board cannot report that", which is noise in a chat context."""
    out = []
    for node in (health or {}).get("nodes", []):
        for comp in node.get("components", []):
            for f in comp.get("findings", []):
                if f.get("severity") not in min_severity:
                    continue
                out.append(
                    f"- {node.get('host','?')}: {f.get('finding','')} "
                    f"[{f.get('severity')}] - {f.get('why','')} "
                    f"Fix: {f.get('fix','') or 'none offered'}")
    return out


def build_context(question: str, status: dict, health: dict,
                  alert_block: str, jobs: list[dict],
                  errors: list[dict]) -> str:
    """Assemble the snapshot. Ordered so the things he is most likely asking
    about are nearest the question at the end."""
    # Local time is computed here, not left to the model. Asking a 24B to
    # subtract four hours produced "17:35 Eastern" for an 18:08 snapshot, and a
    # wrong time is exactly how a routine 3am canary hit once read as a 7am
    # break-in. Hand it the answer; never make it do the arithmetic.
    local = datetime.now().astimezone()
    parts = [f"Snapshot taken {local.strftime('%Y-%m-%d %I:%M %p')} "
             f"{local.tzname()} (Blayne's local time - always quote times to him "
             f"in this zone, and never recompute them yourself).", ""]

    nodes = status.get("odris_nodes") or {}
    reachable = ", ".join(f"{k}={v}" for k, v in nodes.items()) or "unknown"
    parts += [
        "FLEET:",
        f"- node reachability: {reachable}",
        f"- ollama up: {status.get('ollama')}, chat model: {status.get('model')}",
        f"- overall state: {status.get('state')}",
        f"- maintenance: {(status.get('maintenance') or {}).get('active')}",
        "",
    ]

    gpu = status.get("gpu") or {}
    if gpu:
        parts += [f"GPU: up={gpu.get('up')} busy={gpu.get('busy')} "
                  f"loaded={gpu.get('loaded')}", ""]

    found = _findings(health)
    parts += ["HARDWARE FINDINGS:"] + (found or ["- nothing above info level"]) + [""]

    if jobs:
        parts += ["RECENT JOBS:"] + [
            f"- {j.get('id')}: {j.get('title')} [{j.get('status')}"
            f"{'/' + j['review_status'] if j.get('review_status') else ''}]"
            for j in jobs[:5]] + [""]

    if errors:
        parts += ["RECENT ERRORS:"] + [
            f"- {e.get('id')}: {e.get('endpoint')} - {str(e.get('error'))[:160]}"
            for e in errors[:5]] + [""]

    # Last before the question: this is the section he is most often asking
    # about, and position matters more than labelling for a 24B.
    parts += [alert_block or "ALERTS: none active.", "",
              f"Blayne asks: {question}"]
    return "\n".join(parts)
