#!/usr/bin/env python3
"""Forge against a scripted model: every path through generate/test/repair.

    python3 test_forge.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("THUNDER_SANDBOX_ALLOW_NET", "1")
import forge  # noqa: E402

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    PASS += ok
    FAIL += not ok
    print(f"  {'ok  ' if ok else 'FAIL'} {name} {'' if ok else detail}")


def block(code):
    return f"```python\n{code}\n```"


GOOD = "def add(a, b):\n    return a + b"
WRONG = "def add(a, b):\n    return a - b"
BROKEN = "def add(a, b)\n    return a + b"
TESTS = "from solution import *\nassert add(2, 3) == 5\nassert add(-1, 1) == 0\nprint('ALL TESTS PASSED')"
BAD_TESTS = ("from solution import *\nassert add(2, 3) == 5\nassert add(2, 2) == 5\n"
             "print('ALL TESTS PASSED')")


class Script:
    """Decides the model's reply from what it is being asked."""

    def __init__(self, tests, solutions, repair=None, review=None):
        self.tests, self.solutions, self.repair, self.review = tests, list(solutions), repair, review
        self.calls = {"tests": 0, "solve": 0, "repair": 0, "review": 0}
        self.lock = threading.Lock()

    def reply(self, system, user):
        with self.lock:
            if system.startswith("You write tests"):
                if "Every independent solution failed" in user:
                    self.calls["review"] += 1
                    return block(self.review or self.tests)
                self.calls["tests"] += 1
                return block(self.tests)
            if "This attempt fails its tests" in user:
                self.calls["repair"] += 1
                return block(self.repair or WRONG)
            self.calls["solve"] += 1
            return block(self.solutions.pop(0) if self.solutions else WRONG)


def serve(script):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            msgs = body["messages"]
            text = script.reply(msgs[0]["content"], msgs[1]["content"])
            out = json.dumps({"message": {"role": "assistant", "content": text}}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


print("one of several candidates is right")
s = Script(TESTS, [BROKEN, WRONG, GOOD, WRONG])
r = forge.forge("write add(a, b)", serve(s), "m", candidates=4, rounds=2)
check("it passes", r["status"] == "passed", r)
check("the passing candidate is the one returned", r["solution"] == GOOD, r["solution"])
check("no repair was needed", s.calls["repair"] == 0, s.calls)
check("tests were written once, blind", s.calls["tests"] == 1)

print("none right at first, repair fixes it")
s = Script(TESTS, [WRONG, BROKEN], repair=GOOD)
r = forge.forge("write add(a, b)", serve(s), "m", candidates=2, rounds=2)
check("it passes after repair", r["status"] == "passed" and r["solution"] == GOOD, r)
check("one repair round", s.calls["repair"] == 1, s.calls)
check("attempts are counted", r["attempts"] == 3, r["attempts"])

print("the test is what's wrong")
s = Script(BAD_TESTS, [GOOD, GOOD, GOOD], review=TESTS)
r = forge.forge("write add(a, b)", serve(s), "m", candidates=3, rounds=2)
check("every candidate failing the same line triggers a test review", s.calls["review"] == 1, s.calls)
check("correct code survives instead of being 'fixed'", r["status"] == "passed" and r["solution"] == GOOD, r)
check("the result says the tests were revised", r["tests_revised"] is True)

print("never solved")
s = Script(TESTS, [WRONG, WRONG], repair=WRONG)
r = forge.forge("write add(a, b)", serve(s), "m", candidates=2, rounds=2)
check("it reports failure honestly", r["status"] == "failed", r["status"])
check("with the real error attached", "AssertionError" in r.get("last_error", ""), r.get("last_error"))
check("it stops after its repair budget", s.calls["repair"] == 2, s.calls)

print("a candidate that tries to phone home")
EXFIL = ("import socket\ndef add(a, b):\n    s = socket.socket(); s.settimeout(2)\n"
         "    s.connect(('1.1.1.1', 53))\n    return a + b")
s = Script(TESTS, [EXFIL], repair=GOOD)
r = forge.forge("write add(a, b)", serve(s), "m", candidates=1, rounds=1)
if forge.tools.netless_prefix():
    check("network code fails in the sandbox and is repaired away", r["solution"] == GOOD, r["solution"])
else:
    print("  skip (no user namespaces here)")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
