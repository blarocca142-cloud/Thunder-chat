#!/usr/bin/env python3
"""Overnight: read the day's conversations, propose what is worth remembering.

Until now Thunder only remembered when explicitly told to, which means it
remembers almost nothing - nobody stops mid-thought to say "remember that".
Most of what makes a colleague useful is picked up in passing.

The obvious version of this writes straight into memory and is a bad idea. The
claims work already proved what happens when a 24B is trusted unsupervised: it
corrupted an ICD-10 code and dropped a billing provider on the very first real
run. A model quietly writing its own beliefs into its own long-term memory,
every night, with nobody looking, compounds: one confident mistake becomes
permanent context that shapes every later answer, and there is no way to tell
afterwards which facts were real.

So this proposes, and Blayne approves. Nothing reaches memory unreviewed.
That is the same rule as the claims pipeline - draft and flag, submit nothing -
and it is the rule that makes an unattended job safe to run at all.

    ./consolidate.py            # run once, now
    ./consolidate.py --dry-run  # show what it would propose, store nothing
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import memory as mem  # noqa: E402

OLLAMA = "http://127.0.0.1:11434/api/chat"
SERVERUS = "http://10.168.168.13:9001"
MODEL = "thunder:latest"

PAIRS_PER_BATCH = 5      # more than this and the model starts summarising
MAX_TURNS = 400
MIN_LEN, MAX_LEN = 15, 300
# Similar enough to something already known that proposing it is just noise.
KNOWN = 0.88

# A fact hedged is not a fact. If the model is unsure, the honest outcome is to
# propose nothing rather than to record a maybe as if it were true.
HEDGES = re.compile(
    r"(?i)\b(?:maybe|might|may be|possibly|probably|perhaps|seems|appears|"
    r"i think|i believe|not sure|unclear|could be|presumably|apparently)\b")
# Requests and tasks are not durable facts - "make me a video of a car" is a
# thing that happened once, not something true about Blayne.
TASKS = re.compile(
    r"(?i)^(?:make|create|generate|write|build|show|give|send|add|fix|run|"
    r"draw|do)\b")
# The model keeps wanting to write about itself or the conversation.
META = re.compile(
    r"(?i)\b(?:the user|the assistant|this conversation|the chat|as an ai|"
    r"i am thunder|my response)\b")

PROMPT = """You are reading things Blayne said to Thunder, his local AI, to
find facts worth remembering permanently.

A fact is worth keeping ONLY if it will still be true and useful next month:
- Something about Blayne: his work, his family, his tools, what he prefers,
  how he wants things done.
- Something about his machines, network, or software setup.
- A decision he made and the reason for it.

Do NOT extract:
- Anything he asked Thunder to DO. A request is not a fact.
- Anything about this conversation itself.
- Anything you are not certain of. If it is a guess, leave it out.
- Anything that is not stated in the text below. Do not infer, do not fill in
  gaps, and never use anything you happen to know from elsewhere. If Blayne did
  not say it here, it does not exist.

Write each fact as one plain sentence that stands on its own, understandable
with no other context. Name things explicitly - write "Blayne" and the machine
names, never "he" or "it" or "the user".

Return ONLY JSON: {"facts": ["...", "..."]}
If nothing in this excerpt is worth keeping, return {"facts": []}.
That is a perfectly good answer and is usually the right one."""


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def fetch_turns(limit: int = MAX_TURNS) -> list[dict]:
    try:
        with urllib.request.urlopen(f"{SERVERUS}/recent?limit={limit}", timeout=15) as r:
            return json.loads(r.read().decode()).get("turns", [])
    except Exception as e:
        print(f"serverus unreachable: {e}")
        return []


def pair_up(turns: list[dict]) -> list[tuple[str, str]]:
    """Turn a flat role/content list into user/assistant pairs."""
    pairs = []
    pending_user = None
    for t in turns:
        role, content = t.get("role"), (t.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            pending_user = content
        elif role == "assistant" and pending_user:
            pairs.append((pending_user, content))
            pending_user = None
    return pairs


def ask_model(excerpt: str) -> list[str]:
    payload = json.dumps({
        "model": MODEL, "stream": False, "format": "json",
        # Deterministic: this runs unattended, and a different answer every
        # night for the same input would be impossible to reason about.
        "options": {"temperature": 0, "num_predict": 1200},
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": excerpt},
        ],
    }).encode()
    try:
        req = urllib.request.Request(OLLAMA, data=payload,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            body = json.loads(r.read().decode())
        data = json.loads(body["message"]["content"])
    except Exception as e:
        raise ModelBatchError(str(e)) from e
    facts = data.get("facts")
    return [f for f in facts if isinstance(f, str)] if isinstance(facts, list) else []


class ModelBatchError(Exception):
    """The model's output could not be used - usually truncated JSON."""


def facts_from(batch: list[tuple[str, str]], depth: int = 0) -> list[str]:
    """Extract from a batch, splitting it if the model overruns its budget.

    A batch that fails is silently lost otherwise, which is the worst outcome
    for an unattended job: it looks like a clean run that simply found nothing.
    Half the exchanges is half the output, so splitting usually fits.
    """
    excerpt = "\n\n".join(f"Blayne said: {u}" for u, _ in batch)
    try:
        return ask_model(excerpt)
    except ModelBatchError as e:
        if len(batch) == 1 or depth >= 2:
            print(f"    giving up on {len(batch)} exchange(s): {e}")
            return []
        mid = len(batch) // 2
        print(f"    output truncated, splitting {len(batch)} -> {mid}+{len(batch) - mid}")
        return facts_from(batch[:mid], depth + 1) + facts_from(batch[mid:], depth + 1)


def acceptable(fact: str) -> tuple[bool, str]:
    """Mechanical filters, applied before anything reaches the review queue.

    These are cheap and deterministic, and they catch the failure modes this
    model actually has. Anything subtler is Blayne's judgement, which is the
    point of the queue.
    """
    f = " ".join((fact or "").split())
    if len(f) < MIN_LEN:
        return False, "too short"
    if len(f) > MAX_LEN:
        return False, "too long to be one fact"
    if f.endswith("?"):
        return False, "a question, not a fact"
    if HEDGES.search(f):
        return False, "hedged"
    if TASKS.search(f):
        return False, "a request, not a fact"
    if META.search(f):
        return False, "about the conversation, not about Blayne"
    return True, ""


def consolidate(root: Path, dry_run: bool = False) -> dict:
    m = mem.Memory(root)
    state_path = root / "consolidate_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    seen: set[str] = set(state.get("seen", []))

    turns = fetch_turns()
    pairs = pair_up(turns)
    fresh = [(u, a) for u, a in pairs if digest(u + a) not in seen]
    print(f"{len(pairs)} exchanges, {len(fresh)} not yet read")

    pending_path = root / "pending.json"
    pending = json.loads(pending_path.read_text()) if pending_path.exists() else []
    already_pending = {p["text"] for p in pending}

    proposed, rejected = [], []
    for i in range(0, len(fresh), PAIRS_PER_BATCH):
        batch = fresh[i:i + PAIRS_PER_BATCH]
        # Only Blayne's own words are shown to the model. Feeding Thunder's
        # replies back in is how a hallucination becomes a permanent memory:
        # the first dry run proposed "Blayne saves code to /thunder-data/code/
        # on Odris", which he never said - it was Thunder's own invented answer
        # from an hour earlier, on its way to becoming a fact. A model cannot
        # learn its mistakes as truth if it never reads them back. Dropping the
        # replies took the proposals from 13 to 2 and removed every false one.
        print(f"  batch {i // PAIRS_PER_BATCH + 1}: {len(batch)} exchanges", flush=True)
        for fact in facts_from(batch):
            fact = " ".join(fact.split())
            ok, why = acceptable(fact)
            if not ok:
                rejected.append({"text": fact, "why": why})
                continue
            if fact in already_pending:
                continue
            # Already known? Proposing it again just makes the queue tedious,
            # and a tedious queue gets approved without reading.
            vec = m.embed(fact)
            if vec:
                known = any(
                    f.get("vector") and mem.cosine(vec, f["vector"]) > KNOWN
                    for f in m._load())
                if known:
                    rejected.append({"text": fact, "why": "already known"})
                    continue
            entry = {
                "id": digest(fact + utc()),
                "text": fact,
                "proposed": utc(),
                "source": "overnight",
            }
            # Two proposals that are near-identical but not the same sentence
            # are usually one claim made twice with different content - the
            # "favourite colour is orange" / "is cobalt" case. Flag both rather
            # than pick one; a contradiction means neither is trustworthy.
            if vec:
                for other in proposed:
                    if other.get("vector") and mem.cosine(vec, other["vector"]) > 0.82:
                        entry["conflict"] = other["text"]
                        other["conflict"] = fact
                entry["vector"] = vec
            proposed.append(entry)
            already_pending.add(fact)

    report = {
        "at": utc(),
        "exchanges_read": len(fresh),
        "proposed": len(proposed),
        "rejected": len(rejected),
        "rejections": rejected[:20],
    }

    for p in proposed:
        p.pop("vector", None)

    if dry_run:
        return {**report, "facts": proposed, "dry_run": True}

    pending.extend(proposed)
    pending_path.write_text(json.dumps(pending, indent=2))
    # Only mark turns read on a real run, so a dry run does not blind the next
    # real one to the same conversations.
    seen.update(digest(u + a) for u, a in fresh)
    state_path.write_text(json.dumps(
        {"seen": sorted(seen)[-4000:], "last_run": utc()}, indent=2))
    (root / "last_report.json").write_text(json.dumps(report, indent=2))
    return {**report, "facts": proposed}


if __name__ == "__main__":
    root = Path(__file__).parent / "thunder-data" / "memory"
    result = consolidate(root, dry_run="--dry-run" in sys.argv)
    print(f"\nread {result['exchanges_read']} exchanges")
    print(f"proposed {result['proposed']}, rejected {result['rejected']}")
    for f in result.get("facts", []):
        print(f"  + {f['text']}")
    for r in result.get("rejections", [])[:10]:
        print(f"  - [{r['why']}] {r['text'][:70]}")
    if not result.get("dry_run"):
        print("\nNothing has been remembered yet - these are waiting for review.")
