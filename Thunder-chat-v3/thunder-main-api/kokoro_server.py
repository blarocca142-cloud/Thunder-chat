#!/usr/bin/env python3
"""Thunder's voice, on Main's GPU, speaking the same HTTP as Odris did.

Piper on Odris was the right first answer: a self-contained binary on the box
that was not doing anything, deliberately away from the 3090. It has two
problems that only showed up in use. It sounds synthetic, and it reloads its
model on every request, so a reply begins with about 640ms of silence no matter
how short it is.

Kokoro sounds markedly better and, held open in a process instead of respawned,
it starts immediately. The catch was speed: the v0.19 export that was already
on Odris runs at 0.9x real time and does not get faster on the GPU, because its
graph forces 547 copies between host and device. The v1.0 fp16 export measures
7.1x on the 3090 and 2.5x on Main's CPU for the same sentence, which is what
makes this worth doing at all.

So it lives on Main. That is a reversal of the original reasoning and it is
deliberate: a reply is about 0.3s of GPU work and roughly 400MB of VRAM, which
is nothing beside a video render, and the genai server already serialises real
GPU work behind its own lock. Odris keeps Piper, and `/speak` on Main falls
back to it, so a failure here degrades to the old voice rather than to silence.

Same endpoints as Odris:9006, so the app and app.py need no new contract.

    GET  /health
    GET  /voices
    POST /speak   {text, voice, rate} -> audio/wav
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "thunder-nodes" / "odris"))
import kokoro_tts as K                                          # noqa: E402

PORT = int(os.environ.get("KOKORO_PORT", "9012"))
MAX_CHARS = 4000

# The app on the phone already stores one of the Piper names. Those keys have
# to keep working or every installed copy loses its voice on upgrade, so they
# are aliases onto the nearest Kokoro voice rather than a new vocabulary.
LEGACY = {
    "us_male": "am_michael", "us_female": "af_heart",
    "uk_male": "bm_george", "uk_female": "bf_emma",
    "north_male": "bm_daniel", "scots_female": "bf_alice",
    "us_warm": "af_bella", "us_deep": "am_onyx",
    "grump": "am_onyx",
}
RATE_OF = {"grump": 1.12}

_engine: K.Kokoro | None = None
_engine_error: str | None = None
_boot_lock = threading.Lock()


def engine() -> K.Kokoro:
    global _engine, _engine_error
    with _boot_lock:
        if _engine is None:
            _engine = K.Kokoro()
            _engine_error = None
    return _engine


def label_for(voice: str) -> str:
    """A name a person recognises, from a name the model recognises."""
    lang = K.LANG_NAME.get(voice[:1], "")
    sex = {"f": "female", "m": "male"}.get(voice[1:2], "")
    person = voice.split("_", 1)[1].replace("_", " ").title() if "_" in voice else voice
    return f"{person} — {lang} {sex}".strip()


def catalogue() -> dict:
    k = engine()
    out = {}
    for v in k.voices():
        out[v] = {"label": label_for(v), "model": v,
                  "language": K.LANG_NAME.get(v[:1], "?"),
                  "lang_code": K.lang_for(v)}
    # Legacy keys are advertised too, so an old app still sees its own name in
    # the list and does not fall back to the phone's built-in voice.
    for old, new in LEGACY.items():
        if new in out:
            out[old] = dict(out[new], alias_of=new, legacy=True)
    return out


def resolve(voice: str) -> tuple[str, float]:
    v = (voice or "").strip()
    rate = RATE_OF.get(v, 1.0)
    v = LEGACY.get(v, v)
    if not (engine().voice_dir / f"{v}.bin").is_file():
        v = "af_heart"
    return v, rate


def clean_for_speech(text: str) -> str:
    """Strip what should not be read aloud. Same rules Odris uses - code
    blocks, markdown furniture and bare URLs are noise in an ear."""
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"(?im)^\s*prompt\s*:.*$", " ", text)
    text = re.sub(r"[*_#`>|]+", " ", text)
    text = re.sub(r"https?://\S+", " link ", text)
    return re.sub(r"\s+", " ", text).strip()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, obj, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            try:
                k = engine()
                return self._send(200, {"status": "ok", "provider": k.provider,
                                        "voices": len(k.voices()),
                                        "model": str(K.MODEL.name),
                                        "engine": "kokoro"})
            except Exception as e:
                return self._send(503, {"status": "unavailable", "error": str(e)[:200]})
        if self.path == "/voices":
            try:
                return self._send(200, {"voices": catalogue(), "engine": "kokoro"})
            except Exception as e:
                return self._send(503, {"voices": {}, "error": str(e)[:200]})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/speak":
            return self._send(404, {"error": "not found"})
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0)
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})

        text = clean_for_speech(body.get("text") or "")[:MAX_CHARS]
        if not text:
            return self._send(400, {"error": "nothing to say"})
        try:
            voice, base_rate = resolve(body.get("voice") or "af_heart")
            rate = base_rate * float(body.get("rate") or 1.0)
            rate = max(0.5, min(rate, 2.0))
            t = time.time()
            audio = engine().say_long(text, voice, rate)
            wav = K.wav_bytes(audio)
            took = time.time() - t
            secs = audio.size / K.SAMPLE_RATE
            print(f"{voice} {len(text)}ch -> {secs:.2f}s in {took:.2f}s "
                  f"({secs / took if took else 0:.1f}x)", flush=True)
            return self._send(200, wav, "audio/wav")
        except Exception as e:
            return self._send(500, {"error": str(e)[:300]})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    try:
        k = engine()
        print(f"Kokoro ready: {k.provider}, {len(k.voices())} voices, "
              f"{K.MODEL.name}", flush=True)
        # One warm pass, because the first inference of a session compiles
        # kernels and would otherwise land on whoever spoke first.
        k.say("Ready.")
    except Exception as e:
        print(f"Kokoro failed to start: {e}", flush=True)
        sys.exit(1)
    print(f"Thunder TTS on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
