#!/usr/bin/env python3
"""Checks for the tool loop, the Odris gate and the reply guards.

Runs against a fake Ollama and a real gate on loopback - no GPU, no network.
Mostly attacks: patient data leaving, a page reaching back into the LAN, the
model drifting out of English or claiming to be someone else's, invented links,
invented test runs, Odris being down.

    python3 test_tools.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "thunder-nodes" / "odris"))

os.environ["ODRIS_GATE_LOG"] = str(Path(tempfile.mkdtemp()) / "gate.log")
os.environ["ODRIS_GATE_CALLERS"] = "127.0.0.1"

import odris_gate  # noqa: E402
import tools  # noqa: E402
import agent  # noqa: E402

PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def serve(handler) -> str:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


# ---- a fake Ollama that plays back scripted turns ---------------------------

class FakeOllama:
    def __init__(self, turns: list):
        self.turns = list(turns)
        self.requests: list[dict] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                turn = outer.turns.pop(0) if outer.turns else {"content": "(script ran out)"}
                if turn == "NO_TOOLS":
                    msg = b'{"error":"registry.ollama.ai/library/x does not support tools"}'
                    self.send_response(400)
                    self.send_header("Content-Length", str(len(msg)))
                    self.end_headers()
                    self.wfile.write(msg)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                if turn.get("tool_calls"):
                    line = {"message": {"role": "assistant", "content": "",
                                        "tool_calls": turn["tool_calls"]}, "done": False}
                    self.wfile.write((json.dumps(line) + "\n").encode())
                text = turn.get("content", "")
                for i in range(0, len(text), 7):
                    line = {"message": {"role": "assistant", "content": text[i:i + 7]}, "done": False}
                    self.wfile.write((json.dumps(line) + "\n").encode())
                self.wfile.write((json.dumps({"message": {"content": ""}, "done": True}) + "\n").encode())

            def log_message(self, *a):
                pass

            def handle(self):
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the guard hung up mid-stream, which is the point

        self.url = serve(H)


def call(name, **args):
    return {"function": {"name": name, "arguments": args}}


def run_agent(turns, user_text="q", box=None):
    fake = FakeOllama(turns)
    box = box or tools.Toolbox(Path(tempfile.mkdtemp()))
    out = list(agent.run(fake.url, "m", [{"role": "user", "content": user_text}], {}, box, user_text))
    text = "".join(t for k, t in out if k == "text")
    status = [t for k, t in out if k == "status"]
    return text, status, fake, box


# ---- a real gate on loopback, with the internet tools stubbed ---------------

REAL_EXECUTE = odris_gate.execute
odris_gate.execute = lambda tool, args: (
    {"results": [{"title": "Docs", "snippet": "s", "url": "https://docs.example.org/page"}]}
    if tool == "web_search" else
    {"url": args["url"], "title": "T", "text": "page text"})
gate_url = serve(odris_gate.Handler)
tools.GATE = gate_url
os.environ.setdefault("THUNDER_SANDBOX_ALLOW_NET", "1")  # CI boxes may lack user namespaces

print("gate: what is allowed out")
ok, why = odris_gate.decide("web_search", {"query": "python asyncio timeout example"}, "127.0.0.1")
check("an ordinary search is allowed", ok, why)
for q in ["claim for john smith dob 03/14/1961", "patient named Mary Jones S72.001A",
          "ssn 123-45-6789", "member id 88812 aetna", "fracture code S72.001A billing"]:
    ok, why = odris_gate.decide("web_search", {"query": q}, "127.0.0.1")
    check(f"patient-looking search refused: {q!r}", not ok and "patient data" in why, why)
ok, why = odris_gate.decide("web_search", {"query": "x"}, "10.168.168.99")
check("a caller other than Main is refused", not ok, why)
ok, why = odris_gate.decide("rm_rf", {}, "127.0.0.1")
check("a tool not on the list does not exist", not ok, why)
ok, why = odris_gate.decide("web_search", {"query": "x", "evil": 1}, "127.0.0.1")
check("unexpected arguments are refused", not ok, why)
ok, why = odris_gate.decide("web_search", {"query": "x" * 5000}, "127.0.0.1")
check("oversized arguments are refused", not ok, why)

print("gate: no reaching back into the house")
for url in ["http://10.168.168.10:8080/system", "http://127.0.0.1:9005/", "http://localhost/",
            "http://169.254.169.254/latest/meta-data", "file:///etc/passwd", "ftp://x.org/",
            "http://user:pw@example.org/", "http://[::1]/"]:
    ok, why = odris_gate.decide("fetch_url", {"url": url}, "127.0.0.1")
    check(f"refused {url}", not ok, why)
check("a public host passes the address check", odris_gate.public_http_url("https://1.1.1.1/") is None)
check("a redirect onto the LAN is refused",
      odris_gate.public_http_url("http://192.168.1.1/admin") is not None)

print("gate: github")
for args, want in [
    ({"op": "read", "repo": "blarocca142-cloud/Thunder-chat", "path": "README.md"}, True),
    ({"op": "list_repos"}, True),
    ({"op": "read", "repo": "someone-else/secrets", "path": "x"}, False),
    ({"op": "push", "repo": "blarocca142-cloud/Thunder-chat"}, False),
    ({"op": "delete_repo", "repo": "blarocca142-cloud/Thunder-chat"}, False),
    ({"op": "read", "repo": "blarocca142-cloud/Thunder-chat", "path": "../../x"}, False),
    ({"op": "search", "query": "patient named John dob 1/2/1960"}, False),
]:
    ok, why = odris_gate.decide("github", args, "127.0.0.1")
    check(f"github {args.get('op')} {args.get('repo', '')} -> {'allowed' if want else 'refused'}", ok == want, why)
check("the github token is read on Odris, never sent to Main",
      "github_token" not in open(tools.__file__).read())

print("gate: rate limit")
odris_gate._calls["system_status"].clear()
results = [odris_gate.decide("system_status", {}, "127.0.0.1")[0] for _ in range(25)]
check("a runaway loop is capped", results.count(True) == 20 and not results[-1], str(results.count(True)))

print("gate: cache and prefetch")
import time as _t  # noqa: E402
calls = {"search": 0, "fetch": []}
real_ws, real_fetch = odris_gate.web_search, odris_gate.fetch_url
odris_gate.web_search = lambda q, n=6: (calls.__setitem__("search", calls["search"] + 1) or [
    {"title": "a", "snippet": "", "url": "https://1.1.1.1/a"},
    {"title": "b", "snippet": "", "url": "https://1.1.1.1/b"},
    {"title": "lan", "snippet": "", "url": "http://10.168.168.10/secret"}])
odris_gate.fetch_url = lambda u: (calls["fetch"].append(u) or {"url": u, "title": "", "text": "t"})
odris_gate._cache.clear()
r1 = REAL_EXECUTE("web_search", {"query": "cache me"})
r2 = REAL_EXECUTE("web_search", {"query": "cache me"})
check("a repeated search is served from memory", calls["search"] == 1 and r2.get("cached"), str(calls))
_t.sleep(0.5)
check("the top results are fetched before anyone asks",
      sorted(calls["fetch"]) == ["https://1.1.1.1/a", "https://1.1.1.1/b"], str(calls["fetch"]))
check("prefetch never touches a LAN address", "http://10.168.168.10/secret" not in calls["fetch"])
n = len(calls["fetch"])
r3 = REAL_EXECUTE("fetch_url", {"url": "https://1.1.1.1/a"})
check("reading a prefetched page costs no fetch", len(calls["fetch"]) == n and r3.get("cached"), str(r3))
odris_gate.web_search, odris_gate.fetch_url = real_ws, real_fetch

print("tool loop")
text, status, fake, box = run_agent([
    {"tool_calls": [call("run_python", code="print(sum(range(10)))")]},
    {"content": "The sum is 45. I ran it and it printed 45."},
])
tool_msg = [m for m in fake.requests[1]["messages"] if m["role"] == "tool"]
check("the model's code is actually run", tool_msg and '"45' in tool_msg[0]["content"], str(tool_msg))
check("the tool list is sent to the model", "tools" in fake.requests[0])
check("a status line says what it is doing", status == ["running code"], str(status))
check("a true claim of running code is not flagged", "did not actually run" not in text, text)

text, *_ = run_agent([{"content": "I ran the tests and they all pass."}])
check("a false claim of running code is flagged", "did not actually run any code" in text, text)

text, status, fake, box = run_agent([
    {"tool_calls": [call("web_search", query="fastapi release")]},
    {"tool_calls": [call("fetch_url", url="https://docs.example.org/page")]},
    {"content": "See https://docs.example.org/page and also https://made-up.example.com/x."},
])
check("search and fetch go through Odris", [e["tool"] for e in box.log] == ["web_search", "fetch_url"])
check("a link it never opened is flagged", "made-up.example.com" in text.split("---")[-1], text)
check("a link it did open is not flagged", "docs.example.org" not in text.split("---")[-1], text)

text, *_ = run_agent([{"content": "Per https://invented.example.net the answer is 7."}],
                     user_text="what is at https://invented.example.net")
check("a link the user gave is not flagged", "Check:" not in text, text)

text, status, fake, box = run_agent([
    {"tool_calls": [call("web_search", query="patient Mary Jones dob 01/02/1970")]},
    {"content": "I can't search that."},
])
tool_msg = [m for m in fake.requests[1]["messages"] if m["role"] == "tool"]
check("Odris's refusal reaches the model", "patient data" in tool_msg[0]["content"], str(tool_msg))

print("guards")
text, _, fake, _ = run_agent([
    {"content": "Here is the answer: 这是答案"},
    {"content": "Here is the answer in English."},
])
check("a reply drifting into Chinese is never shown", not tools.FOREIGN_SCRIPT.search(text), text)
check("...and is redone in English", "in English" in text, text)
check("...with the model told why", any("English only" in m.get("content", "")
                                        for m in fake.requests[1]["messages"]), "")

long_en = "A" * 100 + "\n"
text, _, fake, _ = run_agent([
    {"content": long_en + "then 中文"},
    {"content": "then the rest."},
])
check("a mid-answer drift keeps the good part and continues",
      text.startswith("A" * 100) and "the rest" in text and not tools.FOREIGN_SCRIPT.search(text), text)

text, *_ = run_agent([
    {"content": "I am Qwen, created by Alibaba Cloud."},
    {"content": "I'm Thunder."},
])
check("claiming to be another lab's model is redone", "Qwen" not in text and "Thunder" in text, text)

text, *_ = run_agent([{"content": "中"}, {"content": "中"}, {"content": "中"}])
check("a model that will not stop drifting is cut off, not shown",
      not tools.FOREIGN_SCRIPT.search(text) and "Stopped" in text, text)

check("ordinary accents are not foreign script", not tools.FOREIGN_SCRIPT.search("café naïve – “ok”"))
check("talking about a company is not an identity claim",
      not tools.LAB_CLAIM.search("Android was made by Google, and I'm going to search Google"))

print("follow-through (seen on Main 2026-09-28)")
text, status, fake, box = run_agent([
    {"content": "I do not know where they are. I will search for it."},
    {"tool_calls": [call("web_search", query="fastapi lifespan docs")]},
    {"content": "Found it."},
])
check("'I will search' with no search gets sent back to actually search",
      [e["tool"] for e in box.log] == ["web_search"] and "Found it." in text, str(box.log))

text, status, fake, box = run_agent([
    {"content": "I can check the arithmetic for you.\n```python\nprint(17 * 23 + 5)\n```"},
    {"tool_calls": [call("run_python", code="print(17 * 23 + 5)")]},
    {"content": "It printed 396."},
], user_text="what is 17*23+5? check it with code")
check("code shown instead of run, when asked to check with code, gets run", box.ran_code and "396" in text, text)

text, status, fake, box = run_agent([{"content": "I will search."}] * 5)
check("a model that only ever promises is stopped after two nudges", len(fake.requests) == 3, str(len(fake.requests)))

text, *_ = run_agent([{"content": "Four"}], user_text="what's 2+2, just answer")
check("a plain answer is not nudged", text == "Four", text)

text, *_ = run_agent([{"content": "Ran that and got the same answer."}])
check("a subjectless claim of running code is flagged", "did not actually run" in text, text)

print("shootout 2026-09-28 fixes")
for phrase in ["The code ran successfully and it printed 396", "It ran:", "And it passed with output:",
               "I already did that. It printed **396**."]:
    text, *_ = run_agent([{"content": phrase}])
    check(f"false run claim flagged: {phrase!r}", "did not actually run" in text, text)
text, *_ = run_agent([{"content": "The function ran in O(n) time."}])
check("'ran in O(n)' is not a run claim", "Check:" not in text, text)

for q in odris_gate._calls.values():
    q.clear()  # the suite makes more calls a minute than the gate's real limits allow
text, status, fake, box = run_agent([
    {"tool_calls": [call("fetch_url", url="https://1.1.1.1/page")]},
    {"content": "Here: **https://1.1.1.1/page**"},
])
check("a fetched link wrapped in bold is not flagged", "unverified" not in text, text)

text, *_ = run_agent([{"content": 'Search said: {"results": [{"title": "x", "url": "https://a.example/b"}]}'}])
check("tool output written with no tool run is flagged as made up", "that output is made up" in text, text)

for q in odris_gate._calls.values():
    q.clear()
text, status, fake, box = run_agent([{"tool_calls": [call("system_status")]}] * agent.MAX_STEPS
                                    + [{"content": ""}, {"content": "From what I found: nothing is wrong."}])
check("out of steps and empty still ends with an answer", "nothing is wrong" in text, text)
check("...written in a final round without tools", "tools" not in fake.requests[-1], "")

text, status, fake, box = run_agent([{"content": ""}])
check("an empty reply is never sent as nothing", "could not put together an answer" in text, text)

box = tools.Toolbox(Path(tempfile.mkdtemp()))
box.forge = lambda task: {"status": "failed", "solution": "x", "tests": "y", "attempts": 4}
out = box.call("forge_code", {"task": "t"})
text = tools.honesty_notes("Here is working code.", box, "")
check("a failed forge result says FAILED to the model", out.get("verdict", "").startswith("FAILED"), str(out))
check("...and to Blayne under the reply", "could not get this code to pass" in text, text)

print("medical routing")
for t in ["claim number 7781 for PT eval", "DOB 01/02/1960", "ICD-10 S72.001A", "fill in the CMS-1500",
          "who is the billing provider", "ssn 123-45-6789"]:
    check(f"medical: {t!r}", tools.looks_medical(t))
for t in ["write a python fizzbuzz", "how do I set up jellyfin", "what's the weather", "fix my bash script"]:
    check(f"not medical: {t!r}", not tools.looks_medical(t))

print("workspace")
ws = Path(tempfile.mkdtemp())
box = tools.Toolbox(ws)
check("write inside the workspace", "saved" in box.call("write_file", {"path": "p/a.py", "content": "x=1"}))
check("read it back", box.call("read_file", {"path": "p/a.py"}).get("content") == "x=1")
for bad in ["../../etc/passwd", "/etc/passwd", "p/../../x"]:
    out = box.call("read_file", {"path": bad})
    check(f"escape refused: {bad}", "error" in out and "content" not in out, str(out))
check("listing works", box.call("list_files", {}).get("files") == ["p/a.py"])

print("sandbox")
out = tools.run_python("import sys; print('hi'); sys.exit(3)")
check("stdout and exit code come back", out.get("stdout", "").strip() == "hi" and out.get("exit_code") == 3, str(out))
out = tools.run_python("while True: pass")
check("an endless loop is killed", out.get("exit_code") != 0, str(out))
if tools.netless_prefix():
    out = tools.run_python("import socket\ns=socket.socket();s.settimeout(3)\n"
                           "try:\n s.connect(('1.1.1.1',53));print('OUT')\nexcept OSError:\n print('BLOCKED')")
    check("sandboxed code has no network", out.get("stdout", "").strip() == "BLOCKED", str(out))
else:
    print("  skip sandboxed code has no network (no user namespaces on this box)")

print("turbo backend (llama-server, OpenAI wire format)")


class FakeLlama:
    """Plays back scripted turns as llama-server SSE, with tool-call
    arguments split into fragments the way the real server sends them."""

    def __init__(self, turns):
        self.turns, self.requests = list(turns), []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                turn = outer.turns.pop(0) if outer.turns else {"content": "(out)"}
                if turn == "NO_JINJA":
                    msg = b'{"error":{"message":"tools param requires --jinja flag"}}'
                    self.send_response(500)
                    self.send_header("Content-Length", str(len(msg)))
                    self.end_headers()
                    self.wfile.write(msg)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()

                def send(delta):
                    self.wfile.write(("data: " + json.dumps({"choices": [{"delta": delta}]}) + "\n\n").encode())
                for i, (name, args) in enumerate(turn.get("calls", [])):
                    raw = json.dumps(args)
                    send({"tool_calls": [{"index": i, "id": f"c{i}", "function": {"name": name, "arguments": ""}}]})
                    for j in range(0, len(raw), 5):
                        send({"tool_calls": [{"index": i, "function": {"arguments": raw[j:j + 5]}}]})
                text = turn.get("content", "")
                for j in range(0, len(text), 6):
                    send({"content": text[j:j + 6]})
                self.wfile.write(b"data: [DONE]\n\n")

            def log_message(self, *a):
                pass

            def handle(self):
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.url = serve(H)


def run_turbo(turns, user_text="q"):
    fake = FakeLlama(turns)
    box = tools.Toolbox(Path(tempfile.mkdtemp()))
    out = list(agent.run(fake.url, "m", [{"role": "user", "content": user_text}], {}, box, user_text,
                         backend="openai"))
    return "".join(t for k, t in out if k == "text"), [t for k, t in out if k == "status"], fake, box


text, status, fake, box = run_turbo([
    {"calls": [("run_python", {"code": "print(6*7)"})]},
    {"content": "It is 42."},
])
tool_msgs = [m for m in fake.requests[1]["messages"] if m["role"] == "tool"]
check("fragmented tool-call arguments are reassembled and run", tool_msgs and "42" in tool_msgs[0]["content"],
      str(tool_msgs))
check("tool results carry the call id the server expects", tool_msgs and tool_msgs[0].get("tool_call_id") == "c0")
asst = [m for m in fake.requests[1]["messages"] if m["role"] == "assistant"][0]
check("the assistant turn is replayed in OpenAI shape",
      asst["tool_calls"][0]["type"] == "function" and isinstance(asst["tool_calls"][0]["function"]["arguments"], str))
check("prompt cache reuse is requested", fake.requests[0].get("cache_prompt") is True)
check("the answer streams through", text == "It is 42.", text)

text, *_ = run_turbo([{"content": "Answer: 答案"}, {"content": "Answer in English."}])
check("the English guard works on the turbo path too", "English" in text and not tools.FOREIGN_SCRIPT.search(text), text)

try:
    run_turbo(["NO_JINJA"])
    check("a server started without tool support falls back", False)
except agent.ToolsUnsupported:
    check("a server started without tool support falls back", True)

text, status, fake, box = run_turbo([
    {"calls": [("web_search", {"query": "a"}), ("system_status", {})]},
    {"content": "done"},
])
check("two tool calls in one turn both run", status == ["searching the web: a", "checking the hardware"], str(status))

print("failure modes")
tools.GATE = "http://127.0.0.1:1"
box = tools.Toolbox(Path(tempfile.mkdtemp()))
out = box.call("run_python", {"code": "print(1)"})
check("Odris down means no tools, not unchecked tools", "refused" in out and not box.ran_code, str(out))
tools.GATE = gate_url
try:
    run_agent(["NO_TOOLS"])
    check("a model without tool support is reported", False)
except agent.ToolsUnsupported:
    check("a model without tool support is reported", True)

text, status, fake, _ = run_agent([{"tool_calls": [call("system_status")]}] * 20 + [{"content": "done"}])
check("the tool loop stops at its step cap and still answers",
      len(status) == agent.MAX_STEPS and text.strip() != "",
      f"{len(status)} steps")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
