#!/usr/bin/env python3
"""Have Thunder read the deck out loud, so the deck is its own demo.

Blayne wanted to be able to say "this was made using Thunder" and mean it. The
narration is the part of that claim with no asterisk on it: the voice is
Kokoro running on Main's own card, the audio never leaves the house, and there
is no subscription behind it.

Run it after editing content.py:

    python3 -m onboarding.narrate            # only what changed
    python3 -m onboarding.narrate --all      # everything, again
    python3 -m onboarding.narrate --voice af_heart

Each slide is cached against a hash of the words it was generated from, so
re-running after fixing one typo re-synthesises one slide instead of
twenty-three.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

from . import content

MAIN = os.environ.get("THUNDER_URL", "http://127.0.0.1:8080")
DATA = Path(os.environ.get(
    "THUNDER_DATA",
    Path(__file__).resolve().parent.parent / "thunder-data"))
AUDIO = DATA / "deck_audio"
INDEX = AUDIO / "index.json"

# Deep American male: this gets played on a television to one person who knows
# IT, and a narrator voice carries better across a room than a bright one.
DEFAULT_VOICE = "am_onyx"


def narration(slide: dict) -> str:
    """What to actually say.

    The short lines, not the detailed ones - spoken word needs less than
    written, and anyone who wants the long version is reading the screen or
    asking Blayne. Each line gets a full stop so the synthesiser breathes
    between them instead of running them into one sentence.
    """
    parts = [slide["title"].rstrip(".") + "."]
    for line in slide["short"]:
        parts.append(line if line.endswith((".", "!", "?")) else line + ".")
    return " ".join(parts)


def speak(text: str, voice: str, timeout: int = 180) -> bytes:
    payload = json.dumps({"text": text, "voice": voice}).encode()
    req = urllib.request.Request(
        f"{MAIN}/speak", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def load_index() -> dict:
    if INDEX.is_file():
        try:
            return json.loads(INDEX.read_text())
        except Exception:
            return {}
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--all", action="store_true",
                    help="re-synthesise every slide, not just changed ones")
    args = ap.parse_args()

    problems = content.validate()
    if problems:
        # Narrating a broken deck wastes GPU time and hides the real error.
        print("content.py has problems; fix these first:", file=sys.stderr)
        for p in problems:
            print("  -", p, file=sys.stderr)
        return 1

    AUDIO.mkdir(parents=True, exist_ok=True)
    index = {} if args.all else load_index()
    made = skipped = failed = 0

    for i, slide in enumerate(content.SLIDES):
        text = narration(slide)
        key = str(i)
        stamp = hashlib.sha1(f"{args.voice}|{text}".encode()).hexdigest()[:16]
        out = AUDIO / f"slide_{i:02d}.wav"
        if index.get(key, {}).get("stamp") == stamp and out.is_file():
            skipped += 1
            continue
        try:
            wav = speak(text, args.voice)
        except Exception as e:
            print(f"  slide {i}: FAILED {e}", file=sys.stderr)
            failed += 1
            continue
        out.write_bytes(wav)
        index[key] = {"stamp": stamp, "voice": args.voice,
                      "bytes": len(wav), "words": len(text.split()),
                      "title": slide["title"]}
        made += 1
        print(f"  slide {i:2d}  {len(wav):>8,}b  {slide['title'][:52]}")

    INDEX.write_text(json.dumps(index, indent=2))
    total = sum(v.get("bytes", 0) for v in index.values())
    print(f"\n{made} generated, {skipped} unchanged, {failed} failed "
          f"- {len(index)}/{len(content.SLIDES)} slides, {total/1_000_000:.1f} MB")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
