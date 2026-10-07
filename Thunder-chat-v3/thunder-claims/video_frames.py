"""Turn a screen recording into stills Claude can look at in seconds.

Blayne records EZClaim (Demo company only - never a real patient on screen,
see the PHI rule in CLAUDE.md), and this cuts the video into one still per
screen change plus contact sheets: 9 stills to a page, each stamped with its
time. Reading three sheets beats scrubbing a video or hunting for one image.

    python3 video_frames.py recording.mp4            # -> ~/ezclaim-study/recording/
    python3 video_frames.py recording.mp4 --out DIR --every 2

Writes:
    frames/0001_00m07s.png ...   every distinct screen, full size
    sheet_01.png ...             3x3 contact sheets, timestamped
    index.txt                    frame -> time, for "go to 2m10s"

Never point --out inside the repo: frames are EZClaim's copyrighted screens.
Needs ffmpeg and Pillow.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

SHEET_COLS, SHEET_ROWS, THUMB_W = 3, 3, 640


def _probe_seconds(video: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        sys.exit(f"ffprobe could not read {video}: {out.stderr.strip()[:200]}")


def _sample(video: Path, every: float, tmp: Path) -> list[tuple[float, Path]]:
    """One frame every `every` seconds. Screen recordings change in jumps, so a
    steady sample plus de-duplication catches every screen without ffmpeg's
    scene filter missing small changes like a dialog opening."""
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps=1/{every}",
                    str(tmp / "%06d.png")], check=True)
    return [((int(p.stem) - 1) * every, p) for p in sorted(tmp.glob("*.png"))]


def _changed(a: Image.Image, b: Image.Image, threshold: float) -> bool:
    small = (160, 90)
    diff = ImageChops.difference(a.convert("L").resize(small), b.convert("L").resize(small))
    return ImageStat.Stat(diff).mean[0] > threshold


def _stamp(t: float) -> str:
    return f"{int(t // 60):02d}m{int(t % 60):02d}s"


def _sheets(kept: list[tuple[float, Path]], out: Path) -> int:
    per = SHEET_COLS * SHEET_ROWS
    n = 0
    for start in range(0, len(kept), per):
        chunk = kept[start:start + per]
        thumbs = []
        for t, p in chunk:
            im = Image.open(p).convert("RGB")
            im = im.resize((THUMB_W, round(im.height * THUMB_W / im.width)))
            ImageDraw.Draw(im).rectangle((0, 0, 120, 26), fill="black")
            ImageDraw.Draw(im).text((6, 6), _stamp(t), fill="yellow")
            thumbs.append(im)
        h = max(im.height for im in thumbs)
        rows = -(-len(thumbs) // SHEET_COLS)
        sheet = Image.new("RGB", (SHEET_COLS * THUMB_W, rows * h), "white")
        for i, im in enumerate(thumbs):
            sheet.paste(im, ((i % SHEET_COLS) * THUMB_W, (i // SHEET_COLS) * h))
        n += 1
        sheet.save(out / f"sheet_{n:02d}.png")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, help="default ~/ezclaim-study/<video name>")
    ap.add_argument("--every", type=float, default=1.0, help="seconds between samples (default 1)")
    ap.add_argument("--threshold", type=float, default=2.0,
                    help="how different a frame must be to count as a new screen (default 2)")
    a = ap.parse_args()
    if not a.video.is_file():
        sys.exit(f"no such file: {a.video}")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not installed")

    out = a.out or Path.home() / "ezclaim-study" / a.video.stem
    frames = out / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    seconds = _probe_seconds(a.video)

    with tempfile.TemporaryDirectory() as tmp:
        kept: list[tuple[float, Path]] = []
        last = None
        for t, p in _sample(a.video, a.every, Path(tmp)):
            im = Image.open(p)
            if last is None or _changed(last, im, a.threshold):
                dest = frames / f"{len(kept) + 1:04d}_{_stamp(t)}.png"
                shutil.copy(p, dest)
                kept.append((t, dest))
                last = im
        if not kept:
            sys.exit("no frames came out of that video")
        n = _sheets(kept, out)

    (out / "index.txt").write_text("".join(f"{p.name}\t{_stamp(t)}\n" for t, p in kept))
    print(f"{a.video.name}: {_stamp(seconds)} long -> {len(kept)} distinct screens, "
          f"{n} contact sheet(s) in {out}")


if __name__ == "__main__":
    main()
