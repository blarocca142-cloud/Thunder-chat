"""Somewhere for code to live.

Coding mode could produce code and then had nowhere to put it: a reply
scrolled off, and the only way off the phone was selecting text by hand.
Images and video have had a store, a media route and a gallery since the
Studio work - code had none of it.

Files are written as real files in real directories, not rows in a database.
That matters more than it sounds: it means the overnight worker can compile
them, `scp` works, a project zips without an export step, and if every other
part of Thunder is switched off the code is still sitting there in a folder.

Projects are just directories. A file belongs to exactly one project, and
"scratch" is where anything unnamed goes.
"""
from __future__ import annotations

import io
import json
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# Extension by fence tag, so a ```python block lands as a .py file. Only the
# tags worth distinguishing - anything unknown becomes .txt, which is honest.
EXTENSIONS = {
    "python": ".py", "py": ".py", "kotlin": ".kt", "kt": ".kt",
    "java": ".java", "javascript": ".js", "js": ".js", "typescript": ".ts",
    "ts": ".ts", "tsx": ".tsx", "jsx": ".jsx", "html": ".html", "css": ".css",
    "bash": ".sh", "sh": ".sh", "shell": ".sh", "zsh": ".sh",
    "json": ".json", "yaml": ".yml", "yml": ".yml", "toml": ".toml",
    "sql": ".sql", "c": ".c", "cpp": ".cpp", "h": ".h", "rust": ".rs",
    "rs": ".rs", "go": ".go", "ruby": ".rb", "php": ".php", "swift": ".swift",
    "xml": ".xml", "markdown": ".md", "md": ".md", "dockerfile": ".dockerfile",
    "gradle": ".gradle", "kts": ".kts", "ini": ".ini", "csv": ".csv",
    "diff": ".diff", "patch": ".patch", "text": ".txt",
}

MAX_BYTES = 2 * 1024 * 1024  # one file; a reply bigger than this is not code
SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_name(name: str, fallback: str = "file") -> str:
    """Reduce anything to a single harmless path segment.

    This is the only thing standing between a filename chosen by a language
    model and the filesystem, so it is deliberately blunt: strip directories,
    refuse dot-entries, allow one dot for the extension.
    """
    name = (name or "").strip().replace("\\", "/").split("/")[-1]
    name = SAFE.sub("_", name).strip("._")
    if not name or name in (".", ".."):
        name = fallback
    return name[:96]


def project_dir(root: Path, project: str, create: bool = False) -> Path:
    d = root / safe_name(project, "scratch")
    # Belt and braces: even after sanitising, confirm the result is still
    # inside the store before anything is written or read.
    if not str(d.resolve()).startswith(str(root.resolve())):
        raise ValueError("project escapes the code store")
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def file_path(root: Path, project: str, name: str) -> Path:
    d = project_dir(root, project)
    p = d / safe_name(name)
    if not str(p.resolve()).startswith(str(d.resolve())):
        raise ValueError("filename escapes the project")
    return p


def guess_name(language: str, content: str, index: int = 0) -> str:
    """Name a block that arrived without one.

    A path in the first lines wins - models habitually write `# app/main.py`
    or `// src/Foo.kt` above the code, and that is a better name than anything
    that can be invented.
    """
    head = "\n".join(content.splitlines()[:4])
    m = re.search(r"""(?m)^\s*(?:#|//|--|/\*)\s*([A-Za-z0-9_./-]+\.[A-Za-z0-9]{1,6})\s*\*?/?\s*$""", head)
    if m:
        return safe_name(m.group(1).split("/")[-1])
    ext = EXTENSIONS.get((language or "").lower().strip(), ".txt")
    # Python classes/functions give a usable name for free.
    m = re.search(r"(?m)^\s*(?:class|def|fun|function)\s+([A-Za-z_][A-Za-z0-9_]*)", content)
    if m:
        return safe_name(m.group(1)) + ext
    stamp = time.strftime("%H%M%S")
    return f"snippet_{stamp}{'' if index == 0 else f'_{index}'}{ext}"


def save(root: Path, content: str, project: str = "scratch",
         filename: str | None = None, language: str = "") -> dict:
    if not content or not content.strip():
        raise ValueError("nothing to save")
    data = content.encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError(f"file is {len(data)} bytes, over the {MAX_BYTES} limit")

    d = project_dir(root, project, create=True)
    name = safe_name(filename) if filename else guess_name(language, content)
    path = d / name
    if not str(path.resolve()).startswith(str(d.resolve())):
        raise ValueError("filename escapes the project")

    existed = path.exists()
    previous = path.read_text(encoding="utf-8", errors="replace") if existed else None
    # Overwriting is usually what is wanted - the model has revised the file -
    # but silently losing the old text is not. One level back is kept.
    if existed and previous != content:
        (d / f".{name}.prev").write_text(previous or "", encoding="utf-8")
    path.write_text(content, encoding="utf-8")

    meta = load_meta(d)
    meta[name] = {
        "name": name,
        "language": (language or "").lower(),
        "bytes": len(data),
        "lines": content.count("\n") + 1,
        "created": meta.get(name, {}).get("created", utc()),
        "updated": utc(),
        "has_previous": existed and previous != content,
    }
    save_meta(d, meta)
    return dict(meta[name], project=d.name, replaced=existed)


def load_meta(d: Path) -> dict:
    p = d / ".index.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def save_meta(d: Path, meta: dict) -> None:
    (d / ".index.json").write_text(json.dumps(meta, indent=2))


def list_projects(root: Path) -> list[dict]:
    out = []
    for d in sorted(root.iterdir()) if root.exists() else []:
        if not d.is_dir():
            continue
        files = [f for f in d.iterdir() if f.is_file() and not f.name.startswith(".")]
        if not files:
            continue
        out.append({
            "project": d.name,
            "files": len(files),
            "bytes": sum(f.stat().st_size for f in files),
            "updated": datetime.fromtimestamp(
                max(f.stat().st_mtime for f in files), timezone.utc).isoformat(),
        })
    return sorted(out, key=lambda p: p["updated"], reverse=True)


def list_files(root: Path, project: str) -> list[dict]:
    d = project_dir(root, project)
    if not d.is_dir():
        return []
    meta = load_meta(d)
    out = []
    for f in sorted(d.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        m = meta.get(f.name, {})
        st = f.stat()
        out.append({
            "name": f.name,
            "language": m.get("language", ""),
            "bytes": st.st_size,
            "lines": m.get("lines"),
            "created": m.get("created"),
            "updated": m.get("updated") or datetime.fromtimestamp(
                st.st_mtime, timezone.utc).isoformat(),
            "has_previous": (d / f".{f.name}.prev").exists(),
        })
    return sorted(out, key=lambda f: f["updated"] or "", reverse=True)


def read(root: Path, project: str, name: str) -> dict | None:
    p = file_path(root, project, name)
    if not p.is_file():
        return None
    meta = load_meta(p.parent).get(p.name, {})
    return {
        "project": p.parent.name,
        "name": p.name,
        "language": meta.get("language", ""),
        "content": p.read_text(encoding="utf-8", errors="replace"),
        "bytes": p.stat().st_size,
        "updated": meta.get("updated"),
    }


def previous(root: Path, project: str, name: str) -> str | None:
    p = file_path(root, project, name)
    prev = p.parent / f".{p.name}.prev"
    return prev.read_text(encoding="utf-8", errors="replace") if prev.is_file() else None


def delete(root: Path, project: str, name: str) -> bool:
    p = file_path(root, project, name)
    if not p.is_file():
        return False
    p.unlink()
    (p.parent / f".{p.name}.prev").unlink(missing_ok=True)
    meta = load_meta(p.parent)
    meta.pop(p.name, None)
    save_meta(p.parent, meta)
    return True


def archive(root: Path, project: str) -> tuple[str, bytes] | None:
    """Zip a project in memory. Small enough that a temp file is not worth it."""
    d = project_dir(root, project)
    if not d.is_dir():
        return None
    files = [f for f in sorted(d.iterdir()) if f.is_file() and not f.name.startswith(".")]
    if not files:
        return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, arcname=f"{d.name}/{f.name}")
    return f"{d.name}.zip", buf.getvalue()
