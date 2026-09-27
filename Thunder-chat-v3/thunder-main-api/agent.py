"""The loop that lets Thunder use its tools.

Ask the model; if it asks for tools, run them (through Odris) and hand back the
results; repeat until it answers. The answer streams to the phone as it is
written, through a guard that stops it the moment it drifts out of English or
claims to be somebody else's model, and has it carry on from that point
properly instead.

Yields (kind, text):
    ("status", "...")  a short line saying what Thunder is doing - searching,
                       reading, running code. Shown, not stored in memory.
    ("text", "...")    the answer itself.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import tools

MAX_STEPS = int(os.environ.get("THUNDER_TOOL_STEPS", "10"))
MAX_REPAIRS = 2
FLUSH_AT = 80  # characters held back for checking before they are shown


class ToolsUnsupported(Exception):
    """The loaded model cannot do tool calls; the caller should use the old path."""


def _post_stream(url: str, payload: dict, timeout: int = 900):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 400 and "does not support tools" in body:
            raise ToolsUnsupported(body) from e
        raise RuntimeError(f"ollama {e.code}: {body[:300]}") from e


def _status_line(name: str, args: dict) -> str:
    if name == "web_search":
        return f"searching the web: {args.get('query', '')}"
    if name == "fetch_url":
        return f"reading {args.get('url', '')}"
    if name == "run_python":
        return "running code"
    if name == "write_file":
        return f"saving {args.get('path', '')}"
    if name == "read_file":
        return f"reading {args.get('path', '')}"
    if name == "memory_search":
        return "checking memory"
    if name == "system_status":
        return "checking the hardware"
    return name


def _one_round(ollama: str, model: str, messages: list[dict], options: dict,
               with_tools: bool, emitted: list[str]):
    """Stream one model turn.

    Yields text that has passed the guard. Returns (tool_calls, violation) via
    StopIteration.value: tool_calls is a list (maybe empty); violation is the
    correction to give the model if the guard tripped, else None.
    """
    payload = {"model": model, "stream": True, "messages": messages, "options": options}
    if with_tools:
        payload["tools"] = tools.SPECS
    think = os.environ.get("THUNDER_THINK")
    if think in ("0", "1"):
        payload["think"] = think == "1"
    calls: list[dict] = []
    pending = ""
    resp = _post_stream(f"{ollama}/api/chat", payload)
    try:
        for raw in resp:
            line = raw.decode().strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = chunk.get("message", {}) or {}
            calls.extend(msg.get("tool_calls") or [])
            piece = msg.get("content") or ""
            if piece:
                pending += piece
                problem = tools.needs_regeneration("".join(emitted)[-200:] + pending)
                if problem:
                    return calls, problem
                if len(pending) >= FLUSH_AT or "\n" in pending:
                    emitted.append(pending)
                    yield pending
                    pending = ""
            if chunk.get("done"):
                break
    finally:
        resp.close()
    if pending:
        problem = tools.needs_regeneration("".join(emitted)[-200:] + pending)
        if problem:
            return calls, problem
        emitted.append(pending)
        yield pending
    return calls, None


def run(ollama: str, model: str, messages: list[dict], options: dict, box: tools.Toolbox,
        user_text: str = ""):
    messages = list(messages)
    steps = 0
    repairs = 0
    emitted: list[str] = []        # answer text shown this turn
    while True:
        allow_tools = steps < MAX_STEPS
        if not allow_tools:
            messages.append({"role": "system", "content":
                             "You have used your tool budget. Answer now with what you have, and say "
                             "plainly what you could not confirm."})
        start = len(emitted)
        gen = _one_round(ollama, model, messages, options, allow_tools, emitted)
        while True:
            try:
                piece = next(gen)
            except StopIteration as stop:
                calls, violation = stop.value
                break
            yield "text", piece

        if violation:
            if repairs >= MAX_REPAIRS:
                yield "text", "\n\n(Stopped: the model kept drifting out of English. Ask again.)"
                break
            repairs += 1
            shown = "".join(emitted)
            if shown:
                messages.append({"role": "assistant", "content": shown})
                messages.append({"role": "user", "content":
                                 violation + " Continue from exactly where you stopped, without "
                                 "repeating anything already written."})
            else:
                messages.append({"role": "system", "content": violation})
            continue

        if calls and not allow_tools:
            # Out of budget and still asking. Its tools were not offered, so
            # these calls are not honoured - stop rather than loop.
            if not "".join(emitted[start:]).strip():
                yield "text", ("I ran out of tool steps before finishing. Here is where it stands: "
                               "I could not confirm an answer. Ask me to continue.")
            break
        if calls:
            steps += 1
            round_text = "".join(emitted[start:])
            messages.append({"role": "assistant", "content": round_text, "tool_calls": calls})
            for call in calls:
                fn = call.get("function", {}) or {}
                name = fn.get("name", "")
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                yield "status", _status_line(name, args)
                result = box.call(name, args)
                messages.append({"role": "tool", "tool_name": name,
                                 "content": json.dumps(result)[:16_000]})
            continue
        break

    reply = "".join(emitted)
    tail = tools.honesty_notes(reply, box, user_text) + tools.sources_footer(box, reply)
    if tail:
        yield "text", tail
