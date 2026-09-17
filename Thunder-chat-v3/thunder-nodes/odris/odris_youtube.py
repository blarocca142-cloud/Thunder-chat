"""Odris: fetch what a YouTube video actually says, so Thunder can read it.

Thunder lives on a box with no route to the internet. Odris is the one machine
that does, narrowly, which is why this runs here and Main only ever talks to
Odris. Nothing about the egress lockdown changes to make this work.

It fetches the captions, not the video. A transcript is what Thunder can
actually use, it is a few tens of kilobytes rather than hundreds of megabytes,
and nothing is ever stored on disk beyond the moment it takes to parse it.

Automatic captions repeat themselves heavily - YouTube emits a rolling window
where each cue restates the tail of the one before, so a ten minute video reads
as three times its real length. The parser removes that, because a transcript
padded threefold wastes most of the context window it is put into.

    ./odris_youtube.py            serve on :9008
    POST /youtube  {"url": "..."}          transcript for one video
    POST /youtube  {"query": "..."}        search, returns candidates
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 9008
HOME = Path(os.path.expanduser("~"))
YTDLP = ["python3", str(HOME / "yt-dlp")]
MAX_TRANSCRIPT = 60000
TIMESTAMP = re.compile(r"^\d\d:\d\d:\d\d\.\d\d\d\s+-->")
TAG = re.compile(r"<[^>]+>")


def run(cmd: list[str], timeout: int = 180) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return False, str(e)


def parse_vtt(text: str) -> str:
    """VTT to plain prose, with the rolling-window duplication removed.

    Automatic captions restate the previous cue's tail on every line. Keeping
    only words that are genuinely new turns a repetitive wall back into
    something readable at roughly its true length.
    """
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if (not line or line == "WEBVTT" or TIMESTAMP.match(line)
                or line.startswith(("Kind:", "Language:", "NOTE"))
                or line.isdigit()):
            continue
        line = TAG.sub("", line).strip()
        if not line:
            continue
        if out and (line == out[-1] or out[-1].endswith(line)):
            continue
        # The common case: this cue starts with the end of the previous one.
        if out:
            prev = out[-1]
            overlap = 0
            words, prev_words = line.split(), prev.split()
            for n in range(min(len(words), len(prev_words)), 0, -1):
                if prev_words[-n:] == words[:n]:
                    overlap = n
                    break
            if overlap:
                line = " ".join(words[overlap:])
        if line:
            out.append(line)
    joined = " ".join(out)
    return re.sub(r"\s+", " ", joined).strip()


def video_info(url: str) -> dict:
    ok, out = run(YTDLP + [
        "--skip-download", "--no-warnings",
        "--print", "%(title)s\t%(channel)s\t%(duration)s\t%(upload_date)s\t%(id)s",
        url], timeout=120)
    if not ok:
        return {"error": "could not read that video: " + out.strip()[-200:]}
    line = next((l for l in out.splitlines() if "\t" in l), "")
    parts = line.split("\t")
    if len(parts) < 5:
        return {"error": "no video found at that link"}
    return {"title": parts[0], "channel": parts[1],
            "seconds": int(parts[2]) if parts[2].isdigit() else None,
            "uploaded": parts[3], "id": parts[4]}


def transcript(url: str) -> dict:
    info = video_info(url)
    if "error" in info:
        return info
    work = Path(tempfile.mkdtemp(prefix="yt_"))
    try:
        base = work / "sub"
        # Auto captions in VTT. No --convert-subs: that needs ffmpeg, which is
        # not on this box, and VTT parses fine here.
        ok, out = run(YTDLP + [
            "--skip-download", "--no-warnings",
            "--write-auto-subs", "--write-subs",
            "--sub-langs", "en.*,en", "--sub-format", "vtt",
            "-o", str(base), url], timeout=300)
        files = sorted(work.glob("*.vtt"))
        if not files:
            info["transcript"] = ""
            info["note"] = ("this video has no captions - nothing to read. "
                            "Only what the title and channel say is known.")
            return info
        text = parse_vtt(files[0].read_text(errors="replace"))
        if len(text) > MAX_TRANSCRIPT:
            text = text[:MAX_TRANSCRIPT] + " [transcript truncated]"
        info["transcript"] = text
        info["chars"] = len(text)
        info["source"] = files[0].name
        return info
    finally:
        shutil.rmtree(work, ignore_errors=True)


def search(query: str, limit: int = 5) -> dict:
    ok, out = run(YTDLP + [
        "--skip-download", "--no-warnings", "--flat-playlist",
        "--print", "%(title)s\t%(channel)s\t%(duration)s\t%(id)s",
        f"ytsearch{limit}:{query}"], timeout=180)
    if not ok:
        return {"error": "search failed: " + out.strip()[-200:], "results": []}
    results = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        p = line.split("\t")
        if len(p) < 4:
            continue
        results.append({"title": p[0], "channel": p[1],
                        "seconds": int(p[2]) if p[2].isdigit() else None,
                        "url": f"https://www.youtube.com/watch?v={p[3]}"})
    return {"query": query, "results": results}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            ok, out = run(YTDLP + ["--version"], timeout=30)
            return self._send(200, {"status": "ok" if ok else "yt-dlp missing",
                                    "version": out.strip()[:20] if ok else None})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/youtube":
            return self._send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", 0))) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        url = (body.get("url") or "").strip()
        query = (body.get("query") or "").strip()
        if url:
            return self._send(200, transcript(url))
        if query:
            return self._send(200, search(query, int(body.get("limit") or 5)))
        return self._send(400, {"error": "give a url or a query"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"Odris YouTube on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
