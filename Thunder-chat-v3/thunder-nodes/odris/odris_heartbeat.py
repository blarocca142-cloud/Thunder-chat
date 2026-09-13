"""Odris: watches Thunder-Cache, Thunder-Engine, and Serverus; reports through
Thunder-Main's /status. Stdlib only, no deps."""
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 9003
CHECK_EVERY = 20  # seconds

TARGETS = {
    "cache": ("10.168.168.11", 22),
    "engine": ("10.168.168.12", 9002),
    "serverus": ("10.168.168.13", 9001),
}

_state = {"odriss": "no_heartbeat", "checked_at": 0, "nodes": {}}
_lock = threading.Lock()


def tcp_up(host: str, port: int, timeout=2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def loop():
    while True:
        nodes = {name: ("up" if tcp_up(h, p) else "down") for name, (h, p) in TARGETS.items()}
        with _lock:
            _state["nodes"] = nodes
            _state["checked_at"] = int(time.time())
            _state["odriss"] = "ok"
        time.sleep(CHECK_EVERY)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/health", "/heartbeat"):
            with _lock:
                return self._send(200, dict(_state))
        return self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Odris heartbeat listening on :{PORT}")
    server.serve_forever()
