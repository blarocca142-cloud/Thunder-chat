"""Odris: watches the fleet and reports through Thunder-Main's /status.

Monitoring is Odris's job, so the whole-fleet view is assembled here rather
than on Main. Main still measures its own GPU and memory - nothing else can
see those - but Odris is what collects, combines and serves the picture.

Stdlib only, no deps."""
import json
import socket
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 9003
CHECK_EVERY = 20  # seconds
MAIN_SYSTEM_URL = "http://10.168.168.10:8080/system"

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


def run(cmd: list[str], timeout: int = 5) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout).stdout.strip()
    except Exception:
        return ""


def local_stats() -> dict:
    """Odris's own health. Cheap enough to take on every heartbeat."""
    out = {"host": socket.gethostname()}
    mem = run(["free", "-m"])
    for line in mem.splitlines():
        c = line.split()
        if c and c[0] == "Mem:" and len(c) >= 7:
            out["ram_total_mb"], out["ram_available_mb"] = int(c[1]), int(c[6])
    df = run(["df", "-BM", "--output=pcent", "/"]).splitlines()
    if len(df) > 1:
        out["disk_used_pct"] = int(df[1].strip().rstrip("%"))
    out["uptime"] = run(["uptime", "-p"])
    # The Radeon is the fleet's post-processing GPU; worth knowing if it cooks.
    temp = run(["sh", "-c",
                "cat /sys/class/drm/card*/device/hwmon/hwmon*/temp1_input 2>/dev/null | head -1"])
    if temp.isdigit():
        out["gpu_temp_c"] = int(temp) // 1000
    return out


def main_system() -> dict:
    """Main measures its own GPU and RAM - Odris cannot see another box's
    hardware, so it asks rather than guesses."""
    try:
        with urllib.request.urlopen(MAIN_SYSTEM_URL, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"unreachable": str(e)}


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
        if self.path == "/fleet":
            # The whole picture in one call: node reachability, Odris's own
            # health, and Main's self-reported hardware.
            with _lock:
                state = dict(_state)
            state["odris"] = local_stats()
            state["main"] = main_system()
            return self._send(200, state)
        return self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Odris heartbeat listening on :{PORT}")
    server.serve_forever()
