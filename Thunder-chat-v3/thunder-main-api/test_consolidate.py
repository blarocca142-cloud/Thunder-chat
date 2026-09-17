#!/usr/bin/env python3
"""Tests for consolidate.py.

This job runs unattended at 3am against a 24B model, which makes it the most
dangerous thing in the system: anything it gets wrong, nobody is watching. The
tests are therefore about containment rather than capability - that bad output
is filtered, that failures are loud instead of silent, and above all that
nothing reaches memory without approval.

The model is stubbed. What is being tested is the machinery around it.

    ./test_consolidate.py
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import consolidate as c  # noqa: E402
import memory as mem  # noqa: E402

WORK = Path(tempfile.mkdtemp(prefix="consoltest_"))
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'pass' if cond else 'FAIL'}  {name}{('  - ' + detail) if detail else ''}")


def main() -> int:
    print("-- what must never become a fact --")
    # Every one of these is something the model actually produced, or the
    # obvious shape of a bad proposal.
    for bad, why in [
        ("Blayne might prefer the 3090 for video", "hedged"),
        ("Blayne probably wants 1080p", "hedged"),
        ("I think Blayne uses odris for voices", "hedged"),
        ("make a video of a car crash", "a request, not a fact"),
        ("Fix the login bug on the android app", "a request, not a fact"),
        ("The user asked about GPUs", "about the conversation, not about Blayne"),
        ("This conversation covered TLS", "about the conversation, not about Blayne"),
        ("What GPU does Blayne use?", "a question, not a fact"),
        ("orange", "too short"),
        ("x" * 400, "too long to be one fact"),
    ]:
        ok, got = c.acceptable(bad)
        check(f"{bad[:40]!r} refused", not ok and got == why, f"ok={ok} why={got!r}")

    print("\n-- what should get through --")
    for good in [
        "Blayne is an A&P aircraft mechanic",
        "Blaynes uncle hand-bills every claim and works 7 days a week",
        "The 3090 on thunder-main is used for video generation",
        "Blayne prefers the zip download for getting code onto his laptop",
    ]:
        ok, why = c.acceptable(good)
        check(f"{good[:44]!r} accepted", ok, why)

    print("\n-- conversations are paired correctly --")
    turns = [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "second question"},
        {"role": "assistant", "content": "second answer"},
        {"role": "user", "content": "dangling with no reply yet"},
    ]
    pairs = c.pair_up(turns)
    check("complete exchanges paired", len(pairs) == 2, str(pairs))
    check("an unanswered message is not paired",
          all("dangling" not in u for u, _ in pairs))
    check("empty turns ignored",
          c.pair_up([{"role": "user", "content": "  "}]) == [])

    print("\n-- the model never sees its own replies --")
    # This is the structural protection. The first real run learned Thunder's
    # own hallucinated file path as a fact about Blayne; it cannot now.
    seen = {}
    c.ask_model = lambda excerpt: seen.setdefault("excerpt", excerpt) and []
    c.facts_from([("what does the vault do", "IT IS ON A USB DRIVE ON ODRIS")])
    excerpt = seen.get("excerpt", "")
    check("Blayne's words are sent", "what does the vault do" in excerpt)
    check("Thunder's reply is NOT sent", "USB DRIVE" not in excerpt, excerpt[:80])

    print("\n-- a truncated batch is retried, not lost --")
    calls = {"n": 0}

    def flaky(excerpt):
        calls["n"] += 1
        # Fail on anything with more than two exchanges, like a real overrun.
        if excerpt.count("Blayne said:") > 2:
            raise c.ModelBatchError("Unterminated string")
        return ["Blayne uses thunder-main for all generation work"]

    c.ask_model = flaky
    batch = [(f"message {i}", f"reply {i}") for i in range(5)]
    facts = c.facts_from(batch)
    check("splitting recovers the batch", len(facts) > 0, f"{len(facts)} facts")
    check("it actually retried", calls["n"] > 1, f"{calls['n']} calls")

    c.ask_model = lambda excerpt: (_ for _ in ()).throw(c.ModelBatchError("always"))
    check("a hopeless batch gives up quietly rather than looping",
          c.facts_from([("one", "two")]) == [])

    print("\n-- nothing reaches memory without approval --")
    root = WORK / "mem"
    root.mkdir(parents=True)
    m = mem.Memory(root)
    m.embed = lambda text: [1.0, 0.0] if "orange" in text else [0.0, 1.0]

    c.fetch_turns = lambda limit=400: [
        {"role": "user", "content": "my favourite colour is orange"},
        {"role": "assistant", "content": "noted"},
    ]
    c.ask_model = lambda excerpt: ["Blaynes favourite colour is orange"]
    mem_orig = mem.Memory
    mem.Memory = lambda r: m  # the consolidator must use our stubbed embedder
    try:
        result = c.consolidate(root)
    finally:
        mem.Memory = mem_orig

    check("a fact was proposed", result["proposed"] == 1, str(result))
    check("the queue holds it", len(json.loads((root / "pending.json").read_text())) == 1)
    # The whole point: proposing is not remembering.
    check("MEMORY IS STILL EMPTY", m.all_facts() == [], str(m.all_facts()))
    check("a report was written", (root / "last_report.json").exists())

    print("\n-- exchanges are not read twice --")
    second = c.consolidate(root)
    check("already-read exchanges are skipped", second["exchanges_read"] == 0, str(second))

    print("\n-- a dry run leaves no trace --")
    root2 = WORK / "mem2"
    root2.mkdir(parents=True)
    m2 = mem.Memory(root2)
    m2.embed = lambda text: [1.0, 0.0]
    mem.Memory = lambda r: m2
    try:
        c.consolidate(root2, dry_run=True)
    finally:
        mem.Memory = mem_orig
    check("dry run writes no queue", not (root2 / "pending.json").exists())
    # If a dry run marked turns as read, the next real run would skip them.
    check("dry run does not mark exchanges as read",
          not (root2 / "consolidate_state.json").exists())

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed: " + ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
