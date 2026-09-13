"""POST /video returns immediately; clients poll GET /creations/{id}."""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import creative
from fastapi.testclient import TestClient

import app as thunder_app

FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 32


def _client(tmp: Path) -> TestClient:
    thunder_app.CREATIONS = tmp
    tmp.mkdir(parents=True, exist_ok=True)
    return TestClient(thunder_app.app)


def test_video_without_hook_is_stub(tmp_path):
    prev = creative.VIDEO_HOOK
    creative.VIDEO_HOOK = ""
    try:
        client = _client(tmp_path)
        res = client.post("/video", json={"prompt": "one spark", "style": "Noir", "duration": 8})
        assert res.status_code == 200
        body = res.json()
        assert body["kind"] == "video"
        assert body["stub"] is True
        assert body["video_url"] is None
        assert body["video_status"] == "stub"
        assert body["url"].startswith("/media/") and body["url"].endswith(".png")
        got = client.get(f"/creations/{body['id']}")
        assert got.status_code == 200
        assert got.json()["video_status"] == "stub"
    finally:
        creative.VIDEO_HOOK = prev


def test_video_hook_returns_immediately_then_flips_done(tmp_path):
    entered = threading.Event()
    release = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            entered.set()
            release.wait(timeout=8)
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(FAKE_MP4)))
            self.end_headers()
            self.wfile.write(FAKE_MP4)

        def log_message(self, *_args):
            return

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    prev = creative.VIDEO_HOOK
    creative.VIDEO_HOOK = f"http://127.0.0.1:{httpd.server_address[1]}/render"
    try:
        client = _client(tmp_path)
        res = client.post("/video", json={"prompt": "slow push", "style": "Cinematic", "duration": 5})
        assert res.status_code == 200
        body = res.json()
        assert body["video_status"] == "processing"
        assert body["video_url"] is None
        assert body["stub"] is True
        assert body["url"].endswith(".png")
        assert entered.wait(timeout=3), "hook was never called"
        still = client.get(f"/creations/{body['id']}").json()
        assert still["video_status"] == "processing"
        release.set()

        deadline = time.monotonic() + 5
        latest = still
        while time.monotonic() < deadline:
            latest = client.get(f"/creations/{body['id']}").json()
            if latest.get("video_status") != "processing":
                break
            time.sleep(0.05)
        assert latest["video_status"] == "done"
        assert latest["video_url"] == f"/media/{body['id']}.mp4"
        assert latest["stub"] is False
        clip = tmp_path / f"{body['id']}.mp4"
        assert clip.is_file()
        assert clip.read_bytes().startswith(b"\x00\x00\x00\x18ftyp")
    finally:
        release.set()
        creative.VIDEO_HOOK = prev
        httpd.shutdown()


def test_video_hook_json_url_is_accepted(tmp_path):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.dumps({"video_url": "http://10.0.0.5:8080/media/out.mp4", "message": "clip ready"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            return

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    prev = creative.VIDEO_HOOK
    creative.VIDEO_HOOK = f"http://127.0.0.1:{httpd.server_address[1]}/render"
    try:
        client = _client(tmp_path)
        res = client.post("/video", json={"prompt": "hold", "style": "Ink", "duration": 5})
        body = res.json()
        deadline = time.monotonic() + 5
        latest = body
        while time.monotonic() < deadline:
            latest = client.get(f"/creations/{body['id']}").json()
            if latest.get("video_status") != "processing":
                break
            time.sleep(0.05)
        assert latest["video_status"] == "done"
        assert latest["video_url"] == "http://10.0.0.5:8080/media/out.mp4"
        assert latest["stub"] is False
    finally:
        creative.VIDEO_HOOK = prev
        httpd.shutdown()
