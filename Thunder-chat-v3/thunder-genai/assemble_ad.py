#!/usr/bin/env python3
"""Turn generated clips into a finished advert.

Raw clips are not a deliverable. What makes an ad look professional is the
finishing: shots cut to a rhythm, a voiceover, music under it, legible titling,
a grade, and the right frame size for where it runs. None of that needs a
better GPU, which is why this exists - the weakest link in the pipeline stops
being generation and becomes editing, and editing is free.

Text is burned in here rather than generated, because diffusion models cannot
render legible lettering. A phone number has to survive being read off a
screen, so it is drawn by ffmpeg.

Usage:
    assemble_ad.py spec.json

Spec:
    {
      "out": "ad.mp4",
      "size": "1080x1920",          # or 1920x1080, 1080x1080
      "voice": "us_male",
      "music": "bed.mp3",           # optional
      "music_gain": -18,            # dB, sits under the voice
      "shots": [
        {"clip": "s1.mp4", "say": "Hurt in a crash?", "text": "INJURED?"},
        {"clip": "s2.mp4", "vo": "line2.mp3", "text": "CALL TODAY"}
      ],
      "end_card": {"lines": ["866-4-HELP-247", "Free consultation - call 24/7"],
                   "seconds": 4, "say": "Call 866 4 HELP 247."}
    }
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

TTS_URL = os.environ.get("TTS_URL", "http://10.168.168.15:9006/speak")
UPSCALER_HOST = os.environ.get("UPSCALE_HOST", "odris")
UPSCALER = "~/postproc/realesrgan-ncnn-vulkan"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)


def probe_duration(path: Path) -> float:
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def say(text: str, voice: str, out: Path) -> float:
    """Voiceover from Odris. Returns duration, or 0 if unavailable - a missing
    voice should cost the narration, not the whole ad."""
    body = json.dumps({"text": text, "voice": voice}).encode()
    req = urllib.request.Request(TTS_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out.write_bytes(r.read())
    except Exception as e:
        print(f"  ! voiceover failed ({e}); continuing silent")
        return 0.0
    return probe_duration(out)


def upscale(clip: Path, work: Path) -> Path:
    """Upscale frames on Odris's GPU. Optional: if that box is unreachable the
    ad still assembles, just softer."""
    frames = work / f"{clip.stem}_frames"
    frames.mkdir(exist_ok=True)
    run(["ffmpeg", "-y", "-i", str(clip), str(frames / "%05d.png")])
    if not any(frames.iterdir()):
        return clip
    remote = f"/tmp/up_{clip.stem}"
    if run(["ssh", "-o", "BatchMode=yes", UPSCALER_HOST,
            f"rm -rf {remote} {remote}_out && mkdir -p {remote} {remote}_out"]).returncode:
        print("  ! upscaler host unreachable; using clip as-is")
        return clip
    run(["scp", "-q", "-r"] + [str(p) for p in sorted(frames.glob("*.png"))] +
        [f"{UPSCALER_HOST}:{remote}/"])
    r = run(["ssh", "-o", "BatchMode=yes", UPSCALER_HOST,
             f"{UPSCALER} -i {remote} -o {remote}_out -s 2 2>/dev/null; ls {remote}_out | wc -l"])
    if not r.stdout.strip().isdigit() or int(r.stdout.strip()) == 0:
        print("  ! upscale produced nothing; using clip as-is")
        return clip
    up = work / f"{clip.stem}_up"
    up.mkdir(exist_ok=True)
    run(["scp", "-q", f"{UPSCALER_HOST}:{remote}_out/*.png", str(up) + "/"])
    if not any(up.iterdir()):
        return clip
    out = work / f"{clip.stem}_up.mp4"
    run(["ffmpeg", "-y", "-framerate", "16", "-i", str(up / "%05d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", str(out)])
    return out if out.exists() else clip


def style_shot(src: Path, out: Path, size: str, text: str | None, seconds: float) -> None:
    """Crop to frame, grade, and burn in titling.

    The grade is deliberate: generated footage tends to look flat and washed,
    and a little contrast and saturation is most of what separates "AI clip"
    from "commercial" at a glance.
    """
    w, h = size.split("x")
    chain = [
        f"scale={w}:{h}:force_original_aspect_ratio=increase",
        f"crop={w}:{h}",
        "eq=contrast=1.12:saturation=1.15:gamma=0.97",
        "unsharp=5:5:0.6",
    ]
    if text:
        safe = text.replace("'", "").replace(":", "\\:")
        chain.append(
            f"drawtext=fontfile={FONT}:text='{safe}':fontcolor=white:fontsize=h/14:"
            f"box=1:boxcolor=black@0.55:boxborderw=24:x=(w-text_w)/2:y=h*0.78"
        )
    run(["ffmpeg", "-y", "-i", str(src), "-t", f"{seconds:.2f}",
         "-vf", ",".join(chain), "-r", "24", "-an",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out)])


def end_card(lines: list[str], size: str, seconds: float, out: Path) -> None:
    """Drawn, not generated - this is the frame that has to be readable."""
    w, h = size.split("x")
    draws = []
    for i, line in enumerate(lines):
        big = i == 0
        safe = line.replace("'", "").replace(":", "\\:")
        draws.append(
            f"drawtext=fontfile={FONT}:text='{safe}':fontcolor=white:"
            f"fontsize=h/{'11' if big else '26'}:x=(w-text_w)/2:"
            f"y=h*{0.42 if big else 0.55 + (i - 1) * 0.07}"
        )
    run(["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"color=c=0x0B1F3A:s={size}:d={seconds}:r=24",
         "-vf", ",".join(draws), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-crf", "18", str(out)])


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    spec = json.loads(Path(sys.argv[1]).read_text())
    base = Path(sys.argv[1]).parent
    size = spec.get("size", "1080x1920")
    voice = spec.get("voice", "us_male")
    work = Path(tempfile.mkdtemp(prefix="ad_"))
    pieces: list[Path] = []
    vo_parts: list[tuple[Path, float]] = []

    try:
        for i, shot in enumerate(spec.get("shots", [])):
            clip = base / shot["clip"]
            if not clip.exists():
                print(f"missing clip: {clip}")
                return 1
            print(f"shot {i + 1}: {clip.name}")

            # A supplied file always wins. Local TTS is fine for a talking
            # assistant and not good enough for broadcast voiceover, so when
            # quality matters the narration comes from outside.
            supplied = shot.get("vo")
            vo = work / f"vo{i}.wav"
            if supplied and (base / supplied).exists():
                run(["ffmpeg", "-y", "-i", str(base / supplied),
                     "-ac", "1", "-ar", "22050", str(vo)])
                vo_len = probe_duration(vo)
            else:
                narration = shot.get("say", "")
                vo_len = say(narration, voice, vo) if narration else 0.0

            # The shot lasts as long as its line needs, never longer than the
            # clip, so narration is never cut off mid-word.
            clip_len = probe_duration(clip)
            seconds = min(clip_len, max(vo_len + 0.4, 2.0)) if vo_len else clip_len

            src = upscale(clip, work) if spec.get("upscale", True) else clip
            styled = work / f"shot{i}.mp4"
            style_shot(src, styled, size, shot.get("text"), seconds)
            pieces.append(styled)
            if vo_len:
                vo_parts.append((vo, seconds))

        ec = spec.get("end_card")
        if ec:
            print("end card")
            secs = float(ec.get("seconds", 4))
            vo = work / "vo_end.wav"
            supplied = ec.get("vo")
            if supplied and (base / supplied).exists():
                run(["ffmpeg", "-y", "-i", str(base / supplied),
                     "-ac", "1", "-ar", "22050", str(vo)])
                vo_len = probe_duration(vo)
            else:
                vo_len = say(ec.get("say", ""), voice, vo) if ec.get("say") else 0.0
            secs = max(secs, vo_len + 0.6)
            card = work / "endcard.mp4"
            end_card(ec.get("lines", []), size, secs, card)
            pieces.append(card)
            if vo_len:
                vo_parts.append((vo, secs))

        if not pieces:
            print("nothing to assemble")
            return 1

        concat = work / "list.txt"
        concat.write_text("".join(f"file '{p}'\n" for p in pieces))
        silent = work / "silent.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
             "-c", "copy", str(silent)])

        # Voice track: each line padded to its shot's length so speech stays
        # locked to picture.
        out = base / spec.get("out", "ad.mp4")
        if vo_parts:
            padded = []
            for j, (vo, seconds) in enumerate(vo_parts):
                p = work / f"pad{j}.wav"
                run(["ffmpeg", "-y", "-i", str(vo), "-af",
                     f"apad=whole_dur={seconds:.2f}", "-t", f"{seconds:.2f}", str(p)])
                padded.append(p)
            vlist = work / "vlist.txt"
            vlist.write_text("".join(f"file '{p}'\n" for p in padded))
            voice_track = work / "voice.wav"
            run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(vlist),
                 "-c", "copy", str(voice_track)])

            music = spec.get("music")
            music_path = base / music if music else None
            if music_path and music_path.exists():
                gain = spec.get("music_gain", -18)
                run(["ffmpeg", "-y", "-i", str(silent), "-i", str(voice_track),
                     "-stream_loop", "-1", "-i", str(music_path),
                     "-filter_complex",
                     f"[2:a]volume={gain}dB[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
                     "-map", "0:v", "-map", "[a]", "-shortest",
                     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)])
            else:
                run(["ffmpeg", "-y", "-i", str(silent), "-i", str(voice_track),
                     "-map", "0:v", "-map", "1:a", "-shortest",
                     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)])
        else:
            shutil.copy(silent, out)

        print(f"\n{out}  {probe_duration(out):.1f}s  {out.stat().st_size / 1e6:.1f} MB")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
