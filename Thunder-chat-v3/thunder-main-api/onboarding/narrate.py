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
SAMPLES = DATA / "voice_samples"

# Bright and quick. The first pick here was am_onyx on the theory that a deep
# voice carries across a room; what it actually did was sound flat and leave
# pauses long enough that Blayne thought the audio had stopped after the title.
# It had not - every file was verified complete - but a narrator who sounds bored
# is the same problem as a broken one.
DEFAULT_VOICE = "am_puck"

# Offered in the presenter so his ears decide rather than my guess.
#
# The seconds are measured, not claimed: every voice reads the identical sample
# line, so the duration is purely pace. That is the one component of "energetic"
# that can be checked rather than asserted, and it lines up with the complaint -
# Onyx takes 10.3s to say what Puck says in 8.6s, a fifth slower, with pauses
# long enough to sound like the audio had stopped.
VOICE_CHOICES = [
    ("am_puck",    "Puck",    "Bright and quick. 8.6s - the fastest of these."),
    ("am_fenrir",  "Fenrir",  "Also 8.6s, with more weight behind it."),
    ("af_heart",   "Heart",   "Friendly and clear. 9.2s."),
    ("af_bella",   "Bella",   "Warm and lively. 10.0s."),
    ("af_nova",    "Nova",    "Crisp and upbeat. 10.2s."),
    ("am_michael", "Michael", "Straightforward American male. 10.5s."),
    ("bm_fable",   "Fable",   "British, storyteller cadence. 10.5s."),
    ("am_onyx",    "Onyx",    "Deep and slow. 10.3s - the one that sounded flat."),
]

SAMPLE_LINE = ("Six computers in a house, running our own AI. "
               "Nothing we do leaves the building. "
               "That last sentence is the entire business.")


def spoken(line: str) -> str:
    """Strip the highlight markers and tidy the punctuation for a synthesiser.

    The `*phrase*` markers are for the screen. Handing them to Kokoro gets them
    voiced or hiccupped over, and a line that already ends in a full stop inside
    its markers otherwise comes out as "...one machine..", which the synthesiser
    reads as an unnaturally long stop.
    """
    text = line.replace("*", "").strip()
    while text.endswith(".."):
        text = text[:-1]
    return text if text.endswith((".", "!", "?")) else text + "."


def narration(slide: dict) -> str:
    """What to actually say.

    The short lines, not the detailed ones - spoken word needs less than
    written, and anyone who wants the long version is reading the screen or
    asking Blayne. Each line gets a full stop so the synthesiser breathes
    between them instead of running them into one sentence.
    """
    parts = [spoken(slide["title"])]
    parts += [spoken(line) for line in slide["short"]]
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


def current_voice() -> str:
    """Whatever the deck was last narrated in, so the picker can show it."""
    idx = load_index()
    voices = {v.get("voice") for v in idx.values() if v.get("voice")}
    return voices.pop() if len(voices) == 1 else DEFAULT_VOICE


def sample(voice: str) -> Path:
    """One fixed line in a given voice, cached on disk.

    The same sentence every time on purpose - comparing voices only works if the
    words do not change underneath them.
    """
    SAMPLES.mkdir(parents=True, exist_ok=True)
    out = SAMPLES / f"{voice}.wav"
    if not out.is_file():
        out.write_bytes(speak(SAMPLE_LINE, voice, timeout=90))
    return out


# Progress for a regeneration kicked off from the presenter, so a phone can show
# something honest instead of a spinner that might mean anything.
PROGRESS: dict = {"running": False, "done": 0, "total": 0, "voice": "", "error": ""}


def regenerate(voice: str) -> dict:
    """Re-narrate every slide in one voice. Blocking; callers thread it.

    Deliberately ignores the cache: the point of calling this is that the voice
    changed, and the cache key includes the voice, so every slide is stale by
    definition.
    """
    problems = content.validate()
    if problems:
        PROGRESS.update({"running": False, "error": "; ".join(problems[:3])})
        return dict(PROGRESS)

    AUDIO.mkdir(parents=True, exist_ok=True)
    PROGRESS.update({"running": True, "done": 0,
                     "total": len(content.SLIDES), "voice": voice, "error": ""})
    index: dict = {}
    try:
        for i, slide in enumerate(content.SLIDES):
            text = narration(slide)
            wav = speak(text, voice)
            (AUDIO / f"slide_{i:02d}.wav").write_bytes(wav)
            index[str(i)] = {
                "stamp": hashlib.sha1(f"{voice}|{text}".encode()).hexdigest()[:16],
                "voice": voice, "bytes": len(wav),
                "words": len(text.split()), "title": slide["title"],
            }
            PROGRESS["done"] = i + 1
        INDEX.write_text(json.dumps(index, indent=2))
    except Exception as e:
        PROGRESS["error"] = str(e)
    finally:
        PROGRESS["running"] = False
    return dict(PROGRESS)


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
