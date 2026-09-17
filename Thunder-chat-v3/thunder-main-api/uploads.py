"""Files Blayne sends Thunder, and turning them into something it can read.

Two routes, decided by what the file actually is:

- **A picture** goes to the vision model, which looks at it. Photos, screenshots,
  a snap of a page.
- **A document** gets its text pulled out and handed to the chat model, which is
  far better at reasoning about words than a 4B vision model is. PDFs, text,
  code, csv, markdown.

A scanned PDF is the awkward middle: no text layer, so the pages are rendered
and read by OCR. That is worse than the vision model at codes and better at
long text, and the reply says which route was taken so a wrong answer can be
traced to how the file was read.

Base64 in JSON rather than multipart, deliberately: the app already speaks
JSON, and this needs no new dependency on a box whose python is 3.14 and where
half the wheels do not exist yet.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

MAX_BYTES = 25 * 1024 * 1024
# Long edge for what goes to the vision model. Small enough to be quick, big
# enough that printed text survives - a phone photo at full size is mostly
# wasted tokens, and a page shrunk too far loses the codes.
VISION_LONG_EDGE = 1600

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic"}
TEXT_EXT = {".txt", ".md", ".csv", ".json", ".py", ".kt", ".java", ".js", ".ts",
            ".html", ".css", ".sh", ".yml", ".yaml", ".toml", ".ini", ".log",
            ".c", ".cpp", ".h", ".rs", ".go", ".rb", ".sql", ".xml", ".diff"}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], timeout: int = 180) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def safe_name(name: str) -> str:
    """One harmless path segment. Same rule as the code vault: the name comes
    from a phone and must never be allowed to point anywhere."""
    name = (name or "").strip().replace("\\", "/").split("/")[-1]
    name = SAFE_NAME.sub("_", name).strip("._")
    return (name or "upload")[:96]


def classify(name: str, blob: bytes) -> str:
    ext = Path(name).suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext == ".pdf":
        return "pdf"
    if ext in TEXT_EXT:
        return "text"
    # No extension to go on: if it decodes as text and is mostly printable,
    # treat it as text. Sniffing beats refusing.
    head = blob[:4096]
    if head.startswith(b"%PDF"):
        return "pdf"
    if head[:8] in (b"\x89PNG\r\n\x1a\n",) or head[:3] == b"\xff\xd8\xff":
        return "image"
    try:
        text = head.decode("utf-8")
    except UnicodeDecodeError:
        return "binary"
    printable = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
    return "text" if printable > len(text) * 0.9 else "binary"


def shrink_for_vision(path: Path, out: Path) -> Path:
    """Downscale for the vision model, keeping text legible."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert("RGB")
            if max(im.size) > VISION_LONG_EDGE:
                scale = VISION_LONG_EDGE / max(im.size)
                im = im.resize((int(im.width * scale), int(im.height * scale)),
                               Image.LANCZOS)
            im.save(out, "JPEG", quality=88)
        return out
    except Exception:
        return path          # send it as-is rather than not at all


def pdf_text(path: Path) -> tuple[str, str]:
    """(text, how). Prefers the real text layer; falls back to OCR."""
    extracted = run(["pdftotext", "-layout", str(path), "-"], timeout=120)
    if extracted and len(extracted.strip()) > 80:
        return extracted, "text layer"
    work = Path(tempfile.mkdtemp(prefix="upl_pdf_"))
    try:
        run(["pdftoppm", "-r", "200", "-png", "-f", "1", "-l", "8",
             str(path), str(work / "p")], timeout=300)
        pages = sorted(work.glob("p*.png"))
        if not pages:
            return "", "could not be rendered"
        text = "\n\n".join(
            run(["tesseract", str(p), "stdout", "--dpi", "200"], timeout=180) or ""
            for p in pages)
        return text, f"OCR of {len(pages)} page(s)"
    finally:
        shutil.rmtree(work, ignore_errors=True)


class Uploads:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.index = root / "index.json"

    def _load(self) -> dict:
        if self.index.is_file():
            try:
                return json.loads(self.index.read_text())
            except json.JSONDecodeError:
                pass
        return {}

    def _save(self, data: dict) -> None:
        tmp = self.index.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self.index)

    def store(self, filename: str, content_b64: str) -> dict:
        try:
            blob = base64.b64decode(content_b64, validate=True)
        except Exception:
            raise ValueError("the file content is not valid base64")
        if not blob:
            raise ValueError("the file is empty")
        if len(blob) > MAX_BYTES:
            raise ValueError(f"{len(blob) // 1024 // 1024} MB is over the "
                             f"{MAX_BYTES // 1024 // 1024} MB limit")

        name = safe_name(filename)
        uid = hashlib.sha256(blob).hexdigest()[:16]
        folder = self.root / uid
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(blob)

        kind = classify(name, blob)
        record = {"id": uid, "name": name, "kind": kind, "bytes": len(blob),
                  "at": utc(), "path": str(path)}

        if kind == "image":
            small = shrink_for_vision(path, folder / "vision.jpg")
            record["vision_path"] = str(small)
            record["how_read"] = "looked at by the vision model"
        elif kind == "pdf":
            text, how = pdf_text(path)
            (folder / "extracted.txt").write_text(text)
            record["text_chars"] = len(text)
            record["how_read"] = how
        elif kind == "text":
            text = blob.decode("utf-8", errors="replace")
            (folder / "extracted.txt").write_text(text)
            record["text_chars"] = len(text)
            record["how_read"] = "read as text"
        else:
            record["how_read"] = "not readable - unknown binary format"

        index = self._load()
        index[uid] = record
        self._save(index)
        return record

    def get(self, uid: str) -> dict | None:
        return self._load().get(uid)

    def listing(self, limit: int = 30) -> list[dict]:
        items = sorted(self._load().values(), key=lambda r: r["at"], reverse=True)
        return items[:limit]

    def text_of(self, uid: str, limit: int = 40000) -> str:
        rec = self.get(uid)
        if not rec:
            return ""
        p = Path(rec["path"]).parent / "extracted.txt"
        if not p.is_file():
            return ""
        text = p.read_text(errors="replace")
        if len(text) > limit:
            # Truncated rather than silently dropped, and it says so, because a
            # model answering off half a document should not sound certain.
            return (text[:limit] +
                    f"\n\n[truncated - {len(text)} characters in total, "
                    f"{limit} shown]")
        return text

    def image_b64(self, uid: str) -> str | None:
        rec = self.get(uid)
        if not rec or rec.get("kind") != "image":
            return None
        p = Path(rec.get("vision_path") or rec["path"])
        if not p.is_file():
            return None
        return base64.b64encode(p.read_bytes()).decode()

    def delete(self, uid: str) -> bool:
        index = self._load()
        rec = index.pop(uid, None)
        if not rec:
            return False
        shutil.rmtree(Path(rec["path"]).parent, ignore_errors=True)
        self._save(index)
        return True
