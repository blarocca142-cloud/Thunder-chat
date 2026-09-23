"""Kokoro on Odris: a voice that does not sound like a satnav.

Piper was chosen because it is a self-contained binary and it works. The
trouble is how it works: `piper` is spawned per request and loads its model
every time, so a reply waits about 640ms before the first sound, whatever the
length of the text. Piper generates at roughly seven times real time, so the
complaint was never throughput - it was the silence at the front.

Kokoro fixes both halves. It is an 82M ONNX model that was already sitting
unused in ~/tts/kokoro, it sounds markedly more natural than Piper's medium
voices, and because it is ONNX it can be held open in this process. The model
loads once at startup and every later request is pure inference.

The one thing Kokoro needs that Piper hides is a phonemizer: it takes IPA, not
text. espeak-ng turns out to already be on this box - bundled inside the Piper
release, one chmod short of usable - so nothing had to be installed and the
egress lockdown never came into it.

Sequence limit is 510 tokens, which is also why text is split on sentences
before synthesis rather than after: it keeps every chunk legal and it is what
lets the caller start playing sentence one while sentence two is still being
made.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import wave
from pathlib import Path

import numpy as np
import onnxruntime as ort

HOME = Path(os.path.expanduser("~"))
# v1.0 fp16, not the v0.19 export that was already on the box. Measured on the
# same sentence and the same machine: v0.19 runs at 0.9x real time whether or
# not it is given the GPU, because its graph forces 547 memory copies between
# host and device and CUDA never gets to help. The v1.0 fp16 export does 7.1x
# on the 3090 and 2.5x on Main's CPU. That is the whole difference between
# replacing Piper and regressing from it.
#
# Do not switch to q8f16 - it segfaults onnxruntime on CPU and emits eight
# times the correct duration of audio on CUDA. q4f16 measures the same speed
# as fp16, so there is nothing to buy with the quality.
MODEL = Path(os.environ.get(
    "KOKORO_MODEL", HOME / "tts" / "kokoro" / "v1" / "model_fp16.onnx"))
VOICE_DIR = Path(os.environ.get(
    "KOKORO_VOICES", HOME / "tts" / "kokoro" / "v1" / "voices"))

# Kokoro's voice names encode their language in the first letter, and espeak
# needs telling which one to phonemize as - the same letters read as different
# sounds in Spanish and English.
LANG_OF = {"a": "en-us", "b": "en-gb", "e": "es", "f": "fr-fr", "h": "hi",
           "i": "it", "j": "ja", "p": "pt-br", "z": "cmn"}
LANG_NAME = {"a": "American English", "b": "British English", "e": "Spanish",
             "f": "French", "h": "Hindi", "i": "Italian", "j": "Japanese",
             "p": "Portuguese", "z": "Mandarin"}


def lang_for(voice: str) -> str:
    return LANG_OF.get(voice[:1], "en-us")

# espeak comes from the system where there is one, and otherwise from inside
# the Piper release, which ships a complete copy. Odris has no system espeak
# and no route to install one, so that bundled binary is the only reason
# Kokoro can run there at all - it just arrived without the execute bit set.
_BUNDLED = HOME / "tts" / "piper"


def _find_espeak() -> tuple[Path, Path | None, Path | None]:
    system = shutil.which("espeak-ng") or shutil.which("espeak")
    if system:
        return Path(system), None, None
    return _BUNDLED / "espeak-ng", _BUNDLED / "espeak-ng-data", _BUNDLED


ESPEAK, ESPEAK_DATA, ESPEAK_LIB = _find_espeak()

SAMPLE_RATE = 24000
MAX_TOKENS = 510            # the style matrix has exactly this many rows

# Kokoro's symbol table. Order matters - the index in this list is the token
# id the model was trained on, so it cannot be sorted, deduplicated or tidied.
_PAD = "$"
_PUNCT = ';:,.!?¡¿—…"«»“” '
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_IPA = ("ɑɐɒæɓʙβɔɕçɗɖðʤəɘɚɛɜɝɞɟʄɡɠɢʛɦɧħɥʜɨɪʝɭɬɫɮʟɱɯɰŋɳɲɴøɵɸθœɶʘɹɺɾɻʀʁɽʂʃʈʧʉʊʋⱱʌɣɤʍχʎʏʑʐʒʔʡʕʢǀǁǂǃˈˌːˑʼʴʰʱʲʷˠˤ˞↓↑→↗↘'̩'ᵻ")
VOCAB = {s: i for i, s in enumerate([_PAD] + list(_PUNCT) + list(_LETTERS) + list(_IPA))}

# espeak emits zero-width joiners inside diphthongs. They are not in the vocab
# and carry no sound, so they would silently become dropped tokens.
_ZERO_WIDTH = re.compile(r"[​-‍﻿]")
_SENTENCE = re.compile(r"(?<=[.!?…])\s+|\n{2,}")


class KokoroUnavailable(RuntimeError):
    """Raised when the model or its phonemizer is not usable on this box."""


class Kokoro:
    def __init__(self, model: Path = MODEL, voice_dir: Path = VOICE_DIR):
        if not model.is_file():
            raise KokoroUnavailable(f"no model at {model}")
        if not ESPEAK.is_file() or not os.access(ESPEAK, os.X_OK):
            raise KokoroUnavailable(
                f"{ESPEAK} is missing or not executable - `chmod +x` it")
        opts = ort.SessionOptions()
        # Odris has four cores and also runs the dashboard, the heartbeat and
        # websearch. Taking all of them for TTS makes the box feel worse than
        # the latency this is meant to fix.
        opts.intra_op_num_threads = 3
        # CUDA where it exists. On CPU this model runs at roughly half real
        # time on Odris's i5-3470, which is slower than the Piper it was meant
        # to replace; on the 3090 it is not close. The provider is therefore
        # the difference between this being an improvement and a regression.
        available = ort.get_available_providers()
        want = os.environ.get("KOKORO_PROVIDER")
        if want:
            providers = [want, "CPUExecutionProvider"]
        elif "CUDAExecutionProvider" in available:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(
            str(model), sess_options=opts, providers=providers)
        self.provider = self.session.get_providers()[0]
        self.voice_dir = voice_dir
        self._styles: dict[str, np.ndarray] = {}
        self._lock = threading.Lock()
        self._env = dict(os.environ)
        if ESPEAK_DATA:
            self._env["ESPEAK_DATA_PATH"] = str(ESPEAK_DATA)
        if ESPEAK_LIB:
            self._env["LD_LIBRARY_PATH"] = str(ESPEAK_LIB)

    # ---- voices -------------------------------------------------------
    def voices(self) -> list[str]:
        return sorted(p.stem for p in self.voice_dir.glob("*.bin"))

    def _style(self, voice: str) -> np.ndarray:
        if voice not in self._styles:
            path = self.voice_dir / f"{voice}.bin"
            if not path.is_file():
                raise KokoroUnavailable(f"no voice {voice}")
            # 510 x 256: one style vector per possible token count, so the
            # row is chosen by the length of what is being said.
            self._styles[voice] = np.fromfile(
                path, dtype=np.float32).reshape(-1, 256)
        return self._styles[voice]

    # ---- text to phonemes to tokens -----------------------------------
    def phonemize(self, text: str, lang: str = "en-us") -> str:
        r = subprocess.run(
            [str(ESPEAK), "-q", "--ipa=3", "-v", lang, text],
            capture_output=True, text=True, env=self._env, timeout=20)
        if r.returncode != 0:
            raise KokoroUnavailable(f"espeak failed: {r.stderr.strip()[:120]}")
        out = _ZERO_WIDTH.sub("", r.stdout)
        return re.sub(r"\s+", " ", out).strip()

    def tokenize(self, phonemes: str) -> list[int]:
        # Unknown symbols are dropped rather than mapped to padding: a wrong
        # token is a wrong sound, whereas a missing one is only a slightly
        # shorter word.
        ids = [VOCAB[c] for c in phonemes if c in VOCAB]
        return ids[:MAX_TOKENS - 2]

    # ---- synthesis -----------------------------------------------------
    def say(self, text: str, voice: str = "af_heart", speed: float = 1.0,
            lang: str | None = None) -> np.ndarray:
        """One chunk of text to 24kHz float32 samples.

        The language follows the voice unless overridden, so a Spanish voice is
        phonemized as Spanish. Getting that wrong does not fail - it produces a
        Spanish speaker reading Spanish words with English letter sounds, which
        is exactly the thing a learner must not be taught.
        """
        tokens = self.tokenize(self.phonemize(text, lang or lang_for(voice)))
        if not tokens:
            return np.zeros(0, dtype=np.float32)
        style = self._style(voice)
        # Padded on both ends, which is what the style row must account for.
        ids = [0] + tokens + [0]
        row = style[min(len(ids), style.shape[0] - 1)]
        with self._lock:          # one ORT session, many HTTP threads
            out = self.session.run(None, {
                "input_ids": np.array([ids], dtype=np.int64),
                "style": row.reshape(1, 256).astype(np.float32),
                "speed": np.array([float(speed)], dtype=np.float32),
            })[0]
        return np.asarray(out, dtype=np.float32).reshape(-1)

    def say_long(self, text: str, voice: str = "af_heart", speed: float = 1.0,
                 lang: str | None = None) -> np.ndarray:
        """Whole replies, split on sentences so nothing exceeds 510 tokens."""
        parts = [p.strip() for p in _SENTENCE.split(text) if p.strip()]
        chunks = [self.say(p, voice, speed, lang) for p in (parts or [text])]
        chunks = [c for c in chunks if c.size]
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        # A short rest between sentences, or they run together and the result
        # sounds hurried in a way the model itself is not.
        gap = np.zeros(int(SAMPLE_RATE * 0.12), dtype=np.float32)
        joined = []
        for i, c in enumerate(chunks):
            if i:
                joined.append(gap)
            joined.append(c)
        return np.concatenate(joined)


def sentences(text: str) -> list[str]:
    """Split for streaming, so the first sentence can play immediately."""
    return [p.strip() for p in _SENTENCE.split(text) if p.strip()]


def _pcm16(samples: np.ndarray) -> np.ndarray:
    """float32 to signed 16-bit, NaNs removed first.

    The fp16 model occasionally emits NaN. np.clip passes NaN straight through
    and the cast to int16 then produces an arbitrary sample, which is an
    audible click. Substituting zero turns that into an inaudible gap.
    """
    clean = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
    return (np.clip(clean, -1.0, 1.0) * 32767.0).astype("<i2")


def to_wav(samples: np.ndarray, path: Path, rate: int = SAMPLE_RATE) -> Path:
    pcm = _pcm16(samples)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return path


def wav_bytes(samples: np.ndarray, rate: int = SAMPLE_RATE) -> bytes:
    import io
    buf = io.BytesIO()
    pcm = _pcm16(samples)
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


if __name__ == "__main__":
    import sys
    import time

    k = Kokoro()
    print("provider:", k.provider)
    print("voices:", ", ".join(k.voices()))
    text = (sys.argv[1] if len(sys.argv) > 1 else
            "Good morning. Let's pick up where we left off yesterday.")
    for voice in k.voices():
        t = time.time()
        audio = k.say_long(text, voice)
        dt = time.time() - t
        secs = audio.size / SAMPLE_RATE
        out = HOME / "tts" / "out" / f"kokoro_{voice}.wav"
        to_wav(audio, out)
        print(f"  {voice:12} {dt:5.2f}s -> {secs:5.2f}s audio "
              f"({secs / dt if dt else 0:4.1f}x real time)  {out.name}")
