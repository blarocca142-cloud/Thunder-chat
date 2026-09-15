"""Image/video studio hooks.

POST /image and POST /video always accept the same JSON the clients send.
If THUNDER_IMAGE_URL or THUNDER_VIDEO_URL is set, the request is forwarded
to that worker. Otherwise Thunder writes a studio stub (still / poster)
so the UI can be built before a real generator is wired.
"""
from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASPECTS = {
    "1:1": (768, 768),
    "16:9": (960, 540),
    "9:16": (540, 960),
    "4:3": (800, 600),
}

STYLE_GROUNDS = {
    "Cinematic": ((28, 32, 40), (18, 16, 14), (196, 163, 90)),
    "Noir": ((12, 12, 14), (28, 28, 32), (180, 180, 184)),
    "Gold hour": ((42, 28, 18), (20, 14, 10), (212, 154, 72)),
    "Raw": ((30, 34, 40), (16, 18, 22), (154, 148, 138)),
    "Documentary": ((24, 30, 28), (14, 18, 16), (140, 168, 148)),
    "Ink": ((16, 18, 22), (10, 10, 12), (237, 232, 223)),
}

IMAGE_HOOK = os.environ.get("THUNDER_IMAGE_URL", "").strip()
VIDEO_HOOK = os.environ.get("THUNDER_VIDEO_URL", "").strip()


def utc_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def new_id(kind: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{kind}_{stamp}_{secrets.token_hex(3)}"


def aspect_size(aspect: str) -> tuple[int, int]:
    return ASPECTS.get(aspect, ASPECTS["1:1"])


def _font(size: int) -> ImageFont.ImageFont:
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size=size)
    return ImageFont.load_default()


def render_stub_png(prompt: str, style: str, aspect: str, kind: str = "image") -> bytes:
    w, h = aspect_size(aspect)
    top, bot, accent = STYLE_GROUNDS.get(style, STYLE_GROUNDS["Cinematic"])
    img = Image.new("RGB", (w, h), bot)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        rgb = tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=rgb)
    inset = max(28, w // 28)
    draw.rectangle([inset, inset, w - inset, h - inset], outline=accent, width=2)
    rule_y = inset + int(h * 0.11)
    draw.line([(inset + 18, rule_y), (w - inset - 18, rule_y)], fill=accent, width=1)
    title = _font(max(18, w // 28))
    body = _font(max(14, w // 36))
    small = _font(max(11, w // 48))
    label = "THUNDER  ·  STUDIO" if kind == "image" else "THUNDER  ·  MOTION"
    draw.text((inset + 22, inset + 16), label, fill=accent, font=small)
    draw.text((inset + 22, rule_y + 16), style or "Cinematic", fill=(237, 232, 223), font=title)
    text = (prompt or "untitled").strip()
    wrapped = _wrap(draw, text, body, w - inset * 2 - 44)
    draw.multiline_text((inset + 22, rule_y + 58), wrapped, fill=(237, 232, 223), font=body, spacing=8)
    foot = (
        "Stub still — set THUNDER_IMAGE_URL for a real generator"
        if kind == "image"
        else "Stub poster — set THUNDER_VIDEO_URL for a real renderer"
    )
    draw.text((inset + 22, h - inset - 36), foot, fill=(154, 148, 138), font=small)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    words = text.split()
    if not words:
        return ""
    lines: list[str] = []
    cur = words[0]
    for word in words[1:]:
        trial = f"{cur} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
        if len(lines) >= 8:
            break
    lines.append(cur)
    return "\n".join(lines[:8])


def forward_hook(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    if "application/json" in ctype:
        return json.loads(raw.decode())
    return {"bytes": raw, "content_type": ctype}


def record(
    *,
    creations_dir: Path,
    kind: str,
    prompt: str,
    style: str,
    aspect: str = "1:1",
    duration: int | None = None,
    png: bytes | None,
    stub: bool,
    message: str,
    extra: dict | None = None,
) -> dict:
    cid = new_id("img" if kind == "image" else "vid")
    # No placeholder image when there is nothing real to show yet. A drawn
    # stand-in with the prompt printed on it reads as "it screenshotted my text
    # instead of making a video".
    url = ""
    if png is not None:
        name = f"{cid}.png"
        (creations_dir / name).write_bytes(png)
        url = f"/media/{name}"
    item = {
        "id": cid,
        "kind": kind,
        "prompt": prompt,
        "style": style,
        "aspect": aspect,
        "duration": duration,
        "url": url,
        "video_url": None,
        "stub": stub,
        "message": message,
        "created": utc_ts(),
    }
    if extra:
        item.update(extra)
    (creations_dir / f"{cid}.json").write_text(json.dumps(item, indent=2))
    return item


def list_creations(creations_dir: Path) -> list[dict]:
    items = []
    for path in creations_dir.glob("*.json"):
        try:
            items.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            continue
    items.sort(key=lambda x: x.get("created", 0), reverse=True)
    return items


def get_creation(creations_dir: Path, cid: str) -> dict | None:
    path = creations_dir / f"{cid}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def update_creation(creations_dir: Path, cid: str, **fields) -> dict | None:
    """Merges fields into an existing creation record - used by the async
    video worker to flip status from 'processing' to 'done'/'error' once
    the (slow) real generation finishes, without blocking the request that
    kicked it off."""
    item = get_creation(creations_dir, cid)
    if item is None:
        return None
    item.update(fields)
    (creations_dir / f"{cid}.json").write_text(json.dumps(item, indent=2))
    return item
