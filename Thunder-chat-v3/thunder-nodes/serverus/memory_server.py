"""Serverus: Thunder's conversation memory. Stdlib only, no deps."""
import json
import sqlite3
import threading
import time
import urllib.parse
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
    # One history per person. Rows from before this existed are Blayne's,
    # because he was the only user; 'owner' is how Main names him.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(turns)")}
    if "who" not in cols:
        conn.execute("ALTER TABLE turns ADD COLUMN who TEXT NOT NULL DEFAULT 'owner'")
        conn.execute("CREATE INDEX IF NOT EXISTS turns_who ON turns (who, id)")
        conn.commit()
    return conn


def _query(path: str) -> dict:
    out = {}
    if "?" in path:
        for part in path.split("?", 1)[1].split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k] = urllib.parse.unquote(v)
    return out


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
            q = _query(self.path)
            try:
                limit = int(q.get("limit", 10))
            except ValueError:
                limit = 10
            who = q.get("who") or "owner"
            with _lock:
                conn = get_conn()
                rows = conn.execute(
                    "SELECT role, content FROM turns WHERE who = ? ORDER BY id DESC LIMIT ?",
                    (who, limit),
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
        who = (body.get("who") or "owner").strip() or "owner"
        reply = (body.get("reply") or "").strip()
        now = int(time.time())
        with _lock:
            conn = get_conn()
            if user_msg:
                conn.execute(
                    "INSERT INTO turns (ts, role, content, who) VALUES (?, 'user', ?, ?)",
                    (now, user_msg, who),
                )
            if reply:
                conn.execute(
                    "INSERT INTO turns (ts, role, content, who) VALUES (?, 'assistant', ?, ?)",
                    (now, reply, who),
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
