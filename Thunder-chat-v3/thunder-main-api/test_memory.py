#!/usr/bin/env python3
"""Tests for memory.py.

Embeddings are stubbed for most of these, so the logic is tested without
needing Ollama up and without depending on a model's exact numbers. One test at
the end uses the real embedder if it is reachable, because the whole point is
recall by meaning and a stub cannot prove that works.

The failure to guard against is memory that quietly fills with rubbish -
duplicates crowding out real facts, a doc ingested twice so a stale copy is
recalled, or "remember what I said?" being stored as a fact.

    ./test_memory.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import memory as mem  # noqa: E402

WORK = Path(tempfile.mkdtemp(prefix="memtest_"))
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'pass' if cond else 'FAIL'}  {name}{('  - ' + detail) if detail else ''}")


def fake_memory(vectors: dict[str, list[float]]) -> mem.Memory:
    """A Memory whose embedder is a lookup table, so similarity is decided by
    the test rather than by a model."""
    m = mem.Memory(WORK / f"m{len(vectors)}{id(vectors)}")
    m.embed = lambda text: vectors.get(" ".join(text.split()), [1.0, 0.0, 0.0])
    return m


def main() -> int:
    print("-- being told to remember --")
    for text, expect in [
        ("remember that odris runs the voices", "odris runs the voices"),
        ("Remember: the 3090 cannot do fp8", "the 3090 cannot do fp8"),
        ("note that my uncle bills by hand", "my uncle bills by hand"),
        ("dont forget the zip is the easy way", "the zip is the easy way"),
        ("keep in mind serverus has the best cpu", "serverus has the best cpu"),
    ]:
        got = mem.extract_instruction(text)
        check(f"{text[:34]!r}", got == expect, f"got {got!r}")

    # Questions and chatter must not become facts. This is the difference
    # between a useful memory and a landfill.
    for text in ["remember what i said about the gpu?", "do you remember me?",
                 "remember", "remember that", "i cant remember", ""]:
        got = mem.extract_instruction(text)
        check(f"not a fact: {text[:32]!r}", got is None, f"stored {got!r}")

    print("\n-- duplicates do not pile up --")
    v = {"the radeon idles at 42C": [1.0, 0.0],
         "the radeon idles at 42 C": [0.999, 0.001],
         "the uncle prints every claim": [0.0, 1.0]}
    m = fake_memory(v)
    m.remember("the radeon idles at 42C")
    m.remember("the radeon idles at 42 C")     # same thing, said differently
    m.remember("the uncle prints every claim")
    facts = m.all_facts()
    check("near-identical facts merged", len(facts) == 2, f"{len(facts)} facts")
    check("the merge was counted, not lost",
          any(f["seen"] == 2 for f in facts), str([f["seen"] for f in facts]))

    print("\n-- recall --")
    v2 = {"query": [1.0, 0.0], "close fact": [0.98, 0.02], "unrelated fact": [0.0, 1.0]}
    m = fake_memory(v2)
    m.remember("close fact")
    m.remember("unrelated fact")
    hits = m.recall("query")
    check("the related fact is recalled", any(h["text"] == "close fact" for h in hits))
    check("the unrelated one is not",
          not any(h["text"] == "unrelated fact" for h in hits), str(hits))
    check("scores are reported", all("score" in h for h in hits))

    m_empty = fake_memory({})
    check("empty memory recalls nothing", m_empty.recall("anything") == [])
    # A dead embedder must mean "no recall", never a crash mid-chat.
    m_dead = mem.Memory(WORK / "dead")
    m_dead.embed = lambda text: None
    m_dead.remember("something worth keeping")
    check("a dead embedder degrades instead of failing",
          m_dead.recall("something") == [])

    print("\n-- documents --")
    doc = """# Title
Intro text that is long enough to be worth keeping as a note on its own.

## First section
Details about the first thing, again long enough to survive the length filter.

## Second section
Details about the second thing, also comfortably past the minimum length.
"""
    m = mem.Memory(WORK / "docs")
    m.embed = lambda text: [1.0, 0.0]
    added = m.ingest("handbook", doc)
    check("document split into notes", added == 3, f"{added} notes")
    texts = [f["text"] for f in m.all_facts()]
    check("sections kept whole with their heading",
          any(t.startswith("## First section") for t in texts), str(texts[:1]))
    check("every note is labelled with its source",
          all(f["source"] == "handbook" for f in m.all_facts()))

    # Re-ingesting must replace. A stale copy of a doc recalled alongside the
    # current one is worse than not having the doc at all.
    again = m.ingest("handbook", doc)
    check("re-ingesting replaces rather than duplicates",
          len(m.all_facts()) == again == 3, f"{len(m.all_facts())} facts")

    m.remember("a hand-written fact that must survive")
    m.ingest("handbook", "# New\nCompletely different content, long enough to keep.")
    kept = [f for f in m.all_facts() if f["source"] != "handbook"]
    check("dropping a source leaves other facts alone", len(kept) == 1, str(kept))

    print("\n-- what goes in the prompt --")
    m = fake_memory({"query": [1.0, 0.0], "close fact": [0.99, 0.01]})
    m.set_profile("PROFILE TEXT")
    m.remember("close fact")
    block = m.recall_block("query")
    check("recall block states the notes are authoritative",
          "THEY WIN" in block, block[:60])
    check("recall block tells it not to mention remembering",
          "mention this list" in block.lower())
    check("profile is not inside the recall block", "PROFILE TEXT" not in block)
    check("no notes means no block", m.recall_block("nothing like it") == "")

    print("\n-- real embeddings (skipped if Ollama is down) --")
    real = mem.Memory(WORK / "real")
    if real.embed("test"):
        real.remember("The Radeon 550 in odris idles around 42C")
        real.remember("Blaynes uncle prints every claim by hand")
        hits = real.recall("how hot does the little gpu get")
        check("recall works on meaning, not shared words",
              bool(hits) and "Radeon" in hits[0]["text"],
              str([h["text"][:40] for h in hits]))
    else:
        print("  skip  Ollama not reachable")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed: " + ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
