"""Odris: neural text-to-speech.

Stock Android TTS sounds robotic, and it also differs on every device. Piper
runs on this box's CPU - never the 3090, which is busy generating - so Thunder
gets one consistent voice wherever it is being used.

Stdlib only, no deps. Piper is a subprocess.
"""
import json
import os
import re
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 9006
HOME = Path(os.path.expanduser("~"))
PIPER = HOME / "tts" / "piper" / "piper"
VOICE_DIR = HOME / "tts" / "voices"
OUT_DIR = HOME / "tts" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Named so the client shows something human, not a filename. speaker is for
# multi-speaker models, where one file holds hundreds of voices.
VOICES = {
    "us_male":        {"model": "en_US-joe-medium",                  "label": "American male"},
    "us_female":      {"model": "en_US-amy-medium",                  "label": "American female"},
    "uk_male":        {"model": "en_GB-alan-medium",                 "label": "British male"},
    "uk_female":      {"model": "en_GB-southern_english_female-low", "label": "British female"},
    "north_male":     {"model": "en_GB-northern_english_male-medium", "label": "Northern English male"},
    "scots_female":   {"model": "en_GB-alba-medium",                 "label": "Scottish female"},
    "us_warm":        {"model": "en_US-lessac-medium",               "label": "American, warm"},
    "us_deep":        {"model": "en_US-ryan-high",                   "label": "American male, richer"},
    # The joke persona. Slightly quick and clipped suits someone who would
    # rather not be talking to you.
    "grump":          {"model": "en_US-amy-medium",                  "label": "Reluctant (joke)",
                       "rate": 1.12},
}

# Keep the last few clips only - they are played once and never wanted again.
KEEP_CLIPS = 40
_lock = threading.Lock()


def available() -> dict:
    out = {}
    for key, v in VOICES.items():
        if (VOICE_DIR / f"{v['model']}.onnx").exists():
            out[key] = {"label": v["label"], "model": v["model"]}
    return out


def prune() -> None:
    clips = sorted(OUT_DIR.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in clips[KEEP_CLIPS:]:
        old.unlink(missing_ok=True)


def speak(text: str, voice: str, speaker: int | None, rate: float) -> Path | None:
    v = VOICES.get(voice) or VOICES["us_male"]
    model = VOICE_DIR / f"{v['model']}.onnx"
    if not model.exists():
        return None
    out = OUT_DIR / f"{int(time.time())}_{uuid.uuid4().hex[:8]}.wav"
    cmd = [str(PIPER), "-m", str(model), "-f", str(out)]
    if speaker is not None:
        cmd += ["-s", str(speaker)]
    # Piper's length scale is inverse: larger is slower.
    rate = float(v.get("rate", 1.0)) * rate  # a voice may carry its own pacing
    cmd += ["--length_scale", f"{1.0 / max(0.5, min(rate, 2.0)):.3f}"]
    try:
        # Piper holds the model in memory per invocation, so one call per
        # request. Generation runs ~13x faster than real time, which is what
        # makes that acceptable.
        subprocess.run(cmd, input=text.encode(), capture_output=True, timeout=120)
    except Exception:
        return None
    return out if out.exists() and out.stat().st_size > 44 else None


def clean_for_speech(text: str) -> str:
    """Strip what should not be read aloud: code blocks, markdown emphasis and
    generation prompts. Reading a prompt out is noise, not information."""
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"(?im)^\s*prompt\s*:.*$", " ", text)
    text = re.sub(r"[*_#`>|]+", " ", text)
    text = re.sub(r"https?://\S+", " link ", text)
    return re.sub(r"\s+", " ", text).strip()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj, content_type="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "voices": len(available())})
        if self.path == "/voices":
            return self._send(200, {"voices": available()})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/speak":
            return self._send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        text = clean_for_speech(body.get("text") or "")
        if not text:
            return self._send(400, {"error": "nothing to say"})
        text = text[:2000]  # a spoken reply past this is a monologue nobody wants
        with _lock:  # one piper at a time; this box has four cores
            path = speak(
                text,
                body.get("voice") or "us_male",
                body.get("speaker"),
                float(body.get("rate") or 1.0),
            )
            prune()
        if not path:
            return self._send(500, {"error": "synthesis failed"})
        return self._send(200, path.read_bytes(), content_type="audio/wav")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"Odris TTS listening on :{PORT} with {len(available())} voices")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
