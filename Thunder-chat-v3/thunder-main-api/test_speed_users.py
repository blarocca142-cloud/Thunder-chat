#!/usr/bin/env python3
"""The request path: how long before the first word, how long before "done",
and whether two people stay two people.

Each call to another machine is given a realistic delay (serverus history,
the embedding for memory recall, engine's safety check, alerts, and the save
afterwards). The model itself is a fake that answers instantly, so what is
measured is purely Thunder's own overhead.

    python3 test_speed_users.py            # this code
    OLD_APP=/path/app_old.py python3 test_speed_users.py   # compare a previous version
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ["THUNDER_DATA"] = tempfile.mkdtemp()
os.environ["THUNDER_AUTH"] = "required"
os.environ["THUNDER_TOOLS"] = "0"         # time the context path, not a tool loop
os.environ.setdefault("THUNDER_SANDBOX_ALLOW_NET", "1")

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    PASS += ok
    FAIL += not ok
    print(f"  {'ok  ' if ok else 'FAIL'} {name} {'' if ok else detail}")


class Ollama(BaseHTTPRequestHandler):
    seen: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Ollama.seen.append(body)
        self.send_response(200)
        self.end_headers()
        for piece in ["Hi ", "there."]:
            self.wfile.write((json.dumps({"message": {"content": piece}, "done": False}) + "\n").encode())
        self.wfile.write((json.dumps({"message": {"content": ""}, "done": True}) + "\n").encode())

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(("127.0.0.1", 0), Ollama)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["OLLAMA_URL"] = f"http://127.0.0.1:{srv.server_address[1]}"

path = Path(os.environ.get("OLD_APP") or HERE / "app.py")
spec = importlib.util.spec_from_file_location("app_under_test", path)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

LAT = {"recent": 0.15, "embed": 0.20, "engine": 0.15, "alerts": 0.05, "append": 0.15}
calls = {"recent_who": [], "append_who": []}


def recent(limit=6, who="owner"):
    time.sleep(LAT["recent"])
    calls["recent_who"].append(who)
    return [{"role": "user", "content": f"earlier message from {who}"}]


def append(u, r, who="owner"):
    time.sleep(LAT["append"])
    calls["append_who"].append(who)


EMBEDS = []


def slow_embed(self, text):
    # A cache in front of the network is part of what is being measured, so
    # it is honoured: a cached text costs nothing, like the real one.
    cache = getattr(self, "_embed_cache", None)
    if cache is not None and text[:2000] in cache:
        return cache[text[:2000]]
    time.sleep(LAT["embed"])
    EMBEDS.append(text[:40])
    vec = [1.0, 0.0, 0.0]
    if cache is not None:
        cache[text[:2000]] = vec
    return vec


app.serverus_recent = recent
app.serverus_append = append
app.engine_check = lambda m: (time.sleep(LAT["engine"]), {"allow": True})[1]
app.alerts.context_block = lambda d: (time.sleep(LAT["alerts"]), "")[1]
app.memory.Memory.embed = slow_embed
app.ollama_up = lambda: True
app.MEM.remember_exchange = lambda a, b: time.sleep(LAT["embed"])
app.MEM.remember("The fleet has five machines and one GPU.", source="test")

from fastapi.testclient import TestClient  # noqa: E402

c = TestClient(app.app)
owner = app.mint_token("blayne-phone")
second = app.mint_token("dad-phone", "dad") if "user" in app.mint_token.__code__.co_varnames else None


def timed(token, message):
    t0 = time.time()
    first = done = None
    with c.stream("POST", "/chat/stream", json={"message": message},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        for line in r.iter_lines():
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("delta") and first is None:
                first = time.time() - t0
            if obj.get("done"):
                done = time.time() - t0
    return first, done


timed(owner, "warm up")
EMBEDS.clear()
runs = [timed(owner, f"how is the fleet {i}") for i in range(5)]
per_msg = len(EMBEDS) / 5
first = sorted(r[0] for r in runs)[2]
done = sorted(r[1] for r in runs)[2]
print(f"{path.name}: first word {first * 1000:.0f} ms, done {done * 1000:.0f} ms, "
      f"{per_msg:.0f} embedding calls per message "
      f"(fleet delays: {', '.join(f'{k} {int(v * 1000)}ms' for k, v in LAT.items())})")

if os.environ.get("OLD_APP"):
    sys.exit(0)

print("speed")
check("fleet lookups overlap instead of queueing (first word under 350 ms)", first < 0.35, f"{first:.3f}s")
check("the message is embedded once, not twice", per_msg <= 1.0, f"{per_msg} per message")
check("the phone is not kept waiting for the save (done within 50 ms of the first word)",
      done - first < 0.05, f"{done - first:.3f}s")

print("two people")
app.MEM.set_profile("PROFILE: this is Blayne")
calls["recent_who"].clear()
Ollama.seen.clear()
timed(second, "hello, who am I?")
sysmsg = Ollama.seen[-1]["messages"][0]["content"]
check("the second user does not get Blayne's profile", "this is Blayne" not in sysmsg)
check("their history is fetched as theirs", calls["recent_who"] == ["dad"], str(calls["recent_who"]))
hist = [m["content"] for m in Ollama.seen[-1]["messages"] if m["role"] == "user"]
check("and contains none of Blayne's messages", not any("from owner" in h for h in hist), str(hist))
time.sleep(0.5)
check("their reply is saved under their name", "dad" in calls["append_who"], str(calls["append_who"]))
check("they get their own memory folder", app.mem_for("dad").root != app.MEM.root)
check("and their own code workspace", app.workspace_for("dad") != app.CODE)
check("names cannot escape the data folder", app.safe_user("../../etc") == "etc")

calls["recent_who"].clear()
Ollama.seen.clear()
timed(owner, "and me?")
sysmsg = Ollama.seen[-1]["messages"][0]["content"]
check("Blayne still gets his own profile", "this is Blayne" in sysmsg)
check("and his own history", calls["recent_who"] == ["owner"], str(calls["recent_who"]))

r = c.post("/chat", json={"message": "hi"})
check("no token, no chat", r.status_code == 401, str(r.status_code))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
