#!/usr/bin/env python3
"""Checks for the onboarding deck.

The failures worth catching here are the ones you cannot see until the deck is
already on a television in front of somebody: a presenter note leaking into the
audience view, a tappable word with no definition, a contents entry pointing at
a chapter that does not exist, or a template placeholder left unsubstituted.

    python3 test_deck.py
"""
import re

from onboarding import content, deck

PASS, FAIL = 0, 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok    {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{('  -> ' + extra) if extra else ''}")


def main():
    print("\ncontent")
    problems = content.validate()
    check("content validates", not problems, "; ".join(problems[:4]))
    check("every section has slides",
          all(any(s["section"] == n for s in content.SLIDES) for n in content.SECTIONS))
    check("contents covers every slide",
          sum(s["count"] for s in content.sections_with_slides()) == len(content.SLIDES))
    check("no slide is only one line",
          all(len(s["short"]) >= 2 for s in content.SLIDES))

    print("\nthe promises we must not break")
    joined = " ".join(
        " ".join(s["short"] + s["detail"]) for s in content.SLIDES).lower()
    check("says patient data is synthetic only", "synthetic" in joined)
    check("says encryption is not compliance",
          "not compliance" in joined or "none of that is compliance" in joined)
    check("names the paperwork gap",
          all(w in joined for w in ("risk analysis", "training")))
    check("admits the fleet's weak spot",
          "one asks for a password" in joined or "trusts anything" in joined)
    check("does not claim HIPAA compliance",
          "we are hipaa compliant" not in joined and "fully compliant" not in joined)

    print("\naudience view leaks nothing")
    audience = deck.audience_html()
    notes = [s["notes"] for s in content.SLIDES]
    leaked = [n[:40] for n in notes if n[:40] in audience]
    check("no presenter note appears in the audience HTML", not leaked,
          str(leaked[:2]))
    check("glossary is absent from the audience view",
          not any(d[:40] in audience for d in content.GLOSSARY.values()))
    check("audience view has no notes element", 'id="notes"' not in audience)

    print("\npresenter view has everything")
    pres = deck.presenter_html()
    check("presenter has the notes element", 'id="notes"' in pres)
    check("presenter carries every note",
          all(n[:40] in pres for n in notes))
    check("presenter has the contents menu", 'id="tocBtn"' in pres)
    check("presenter has narration controls",
          'id="speakBtn"' in pres and 'id="autoBtn"' in pres)

    print("\ntemplates rendered")
    for name, html in (("audience", audience), ("presenter", pres)):
        check(f"{name}: no placeholder left",
              "__CSS__" not in html and "__PAYLOAD__" not in html)
        check(f"{name}: exactly one script block", html.count("<script>") == 1)
        check(f"{name}: state url is absolute",
              "fetch('state'" not in html)
        js = re.search(r"<script>(.*?)</script>", html, re.S)
        check(f"{name}: script block closes", js is not None)
        # The Odris dashboard bug: a Python-interpreted escape breaking a JS
        # string. If it happened, the payload would contain a raw newline
        # inside a quoted value.
        check(f"{name}: payload survived as one line",
              "\n" not in re.search(r"const DATA = (.*)", html).group(1))

    print("\nstate machine")
    deck.set_state(slide=0, detail=False)
    start = deck.get_state()
    check("starts where it was set", start["slide"] == 0)
    r1 = deck.set_state(slide=5)
    check("moves", r1["slide"] == 5)
    check("rev increments", r1["rev"] > start["rev"])
    check("detail untouched by a move", r1["detail"] is False)
    check("clamps past the end",
          deck.set_state(slide=9999)["slide"] == len(content.SLIDES) - 1)
    check("clamps before the start", deck.set_state(slide=-10)["slide"] == 0)
    r2 = deck.set_state(detail=True)
    check("detail toggles without moving", r2["detail"] and r2["slide"] == 0)
    before = deck.get_state()["rev"]
    deck.set_state()
    check("a no-op still bumps rev so a poll cannot miss it",
          deck.get_state()["rev"] > before)
    deck.set_state(slide=0, detail=False)

    print("\nnarration text")
    from onboarding import narrate
    for i, s in enumerate(content.SLIDES):
        text = narrate.narration(s)
        if not text.strip().endswith((".", "!", "?")):
            check(f"slide {i} narration ends in punctuation", False, text[-30:])
            break
    else:
        check("every slide's narration ends in punctuation", True)
    check("narration includes the title",
          content.SLIDES[0]["title"].rstrip(".") in narrate.narration(content.SLIDES[0]))
    check("narration does not read the presenter notes",
          content.SLIDES[0]["notes"][:30] not in narrate.narration(content.SLIDES[0]))

    print(f"\n{PASS} passed, {FAIL} failed\n")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
