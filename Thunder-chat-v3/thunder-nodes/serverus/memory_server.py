"""Serverus: Thunder's conversation memory. Stdlib only, no deps."""
import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 9001
DB_PATH = Path.home() / "serverus-data" / "memory.db"
DB_PATH.parent.mkdir(exist_ok=True)

_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS turns ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts INTEGER, role TEXT, content TEXT)"
    )
    return conn


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        if self.path.startswith("/recent"):
            limit = 10
            if "?" in self.path:
                q = self.path.split("?", 1)[1]
                for part in q.split("&"):
                    if part.startswith("limit="):
                        try:
                            limit = int(part.split("=", 1)[1])
                        except ValueError:
                            pass
            with _lock:
                conn = get_conn()
                rows = conn.execute(
                    "SELECT role, content FROM turns ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                conn.close()
            rows.reverse()
            return self._send(200, {"turns": [{"role": r, "content": c} for r, c in rows]})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/append":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        user_msg = (body.get("user") or "").strip()
        reply = (body.get("reply") or "").strip()
        now = int(time.time())
        with _lock:
            conn = get_conn()
            if user_msg:
                conn.execute(
                    "INSERT INTO turns (ts, role, content) VALUES (?, 'user', ?)",
                    (now, user_msg),
                )
            if reply:
                conn.execute(
                    "INSERT INTO turns (ts, role, content) VALUES (?, 'assistant', ?)",
                    (now, reply),
                )
            conn.commit()
            conn.close()
        return self._send(200, {"ok": True})

    def log_message(self, fmt, *args):
        pass  # keep it quiet; nohup.out would otherwise grow forever


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Serverus memory listening on :{PORT}, db at {DB_PATH}")
    server.serve_forever()
