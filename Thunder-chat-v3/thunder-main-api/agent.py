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
        if (e.code == 400 and "does not support tools" in body) or "--jinja" in body:
            raise ToolsUnsupported(body) from e
        raise RuntimeError(f"ollama {e.code}: {body[:300]}") from e


def _status_line(name: str, args: dict) -> str:
    if name == "web_search":
        return f"searching the web: {args.get('query', '')}"
    if name == "fetch_url":
        return f"reading {args.get('url', '')}"
    if name == "run_python":
        return "running code"
    if name == "forge_code":
        return "running code - forge: tests, candidates, repair"
    if name == "write_file":
        return f"saving {args.get('path', '')}"
    if name == "read_file":
        return f"reading {args.get('path', '')}"
    if name == "github":
        what = args.get("path") or args.get("query") or args.get("repo") or ""
        return f"reading github: {args.get('op', '')} {what}".strip()
    if name == "memory_search":
        return "checking memory"
    if name == "icd10_lookup":
        return f"checking the official code list: {args.get('codes', '')}"
    if name == "system_status":
        return "checking the hardware"
    return name


def _stream_ollama(base: str, model: str, messages: list[dict], options: dict, with_tools: bool):
    """Ollama's native API. Yields ("text", str) and ("call", {id, name, arguments})."""
    payload = {"model": model, "stream": True, "messages": messages, "options": options}
    if with_tools:
        payload["tools"] = tools.SPECS
    think = os.environ.get("THUNDER_THINK")
    if think in ("0", "1"):
        payload["think"] = think == "1"
    resp = _post_stream(f"{base}/api/chat", payload)
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
            for c in msg.get("tool_calls") or []:
                fn = c.get("function", {}) or {}
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                yield "call", {"id": c.get("id", ""), "name": fn.get("name", ""), "arguments": args}
            if msg.get("content"):
                yield "text", msg["content"]
            if chunk.get("done"):
                break
    finally:
        resp.close()


def _stream_openai(base: str, model: str, messages: list[dict], options: dict, with_tools: bool):
    """llama.cpp's llama-server (OpenAI-compatible). This is the Turbo path:
    speculative decoding and prompt-cache reuse live in the server, so nothing
    here changes except the wire format. Tool-call arguments arrive as string
    fragments across chunks and are assembled by index."""
    payload = {"model": model, "stream": True, "messages": messages,
               "temperature": options.get("temperature", 0.6),
               "max_tokens": options.get("num_predict", 4096),
               "repeat_penalty": options.get("repeat_penalty", 1.0),
               "cache_prompt": True}
    if with_tools:
        payload["tools"] = tools.SPECS
    partial: dict[int, dict] = {}
    resp = _post_stream(f"{base}/v1/chat/completions", payload)
    try:
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                for tc in delta.get("tool_calls") or []:
                    slot = partial.setdefault(tc.get("index", 0), {"id": "", "name": "", "args": ""})
                    slot["id"] = tc.get("id") or slot["id"]
                    fn = tc.get("function") or {}
                    slot["name"] += fn.get("name") or ""
                    slot["args"] += fn.get("arguments") or ""
                if delta.get("content"):
                    yield "text", delta["content"]
    finally:
        resp.close()
    for i in sorted(partial):
        slot = partial[i]
        try:
            args = json.loads(slot["args"]) if slot["args"].strip() else {}
        except json.JSONDecodeError:
            args = {}
        yield "call", {"id": slot["id"] or f"call_{i}", "name": slot["name"], "arguments": args}


def _one_round(base: str, model: str, messages: list[dict], options: dict,
               with_tools: bool, emitted: list[str], backend: str = "ollama", user_text: str = ""):
    """Stream one model turn through the guard.

    Yields text that has passed. Returns (calls, violation) via
    StopIteration.value: calls is a list of {id, name, arguments}; violation is
    the correction to give the model if the guard tripped, else None.
    """
    stream = (_stream_openai if backend == "openai" else _stream_ollama)(
        base, model, messages, options, with_tools)
    calls: list[dict] = []
    pending = ""
    try:
        for kind, value in stream:
            if kind == "call":
                calls.append(value)
                continue
            pending += value
            tail = "".join(emitted)[-200:]
            problem = tools.needs_regeneration(tail + pending, user_text, len(tail))
            if problem:
                return calls, problem
            if len(pending) >= FLUSH_AT or "\n" in pending:
                emitted.append(pending)
                yield pending
                pending = ""
    finally:
        stream.close()
    if pending:
        tail = "".join(emitted)[-200:]
        problem = tools.needs_regeneration(tail + pending, user_text, len(tail))
        if problem:
            return calls, problem
        emitted.append(pending)
        yield pending
    return calls, None


def _record_calls(messages: list[dict], text: str, calls: list[dict], backend: str) -> None:
    if backend == "openai":
        messages.append({"role": "assistant", "content": text or None, "tool_calls": [
            {"id": c["id"], "type": "function",
             "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}} for c in calls]})
    else:
        messages.append({"role": "assistant", "content": text, "tool_calls": [
            {"function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls]})


def _record_result(messages: list[dict], call: dict, result: dict, backend: str) -> None:
    content = json.dumps(result)[:16_000]
    if backend == "openai":
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": content})
    else:
        messages.append({"role": "tool", "tool_name": call["name"], "content": content})


def run(base: str, model: str, messages: list[dict], options: dict, box: tools.Toolbox,
        user_text: str = "", backend: str = "ollama"):
    messages = list(messages)
    steps = 0
    repairs = 0
    nudges = 0
    emitted: list[str] = []        # answer text shown this turn
    while True:
        allow_tools = steps < MAX_STEPS
        if not allow_tools:
            messages.append({"role": "system", "content":
                             "You have used your tool budget. Answer now with what you have, and say "
                             "plainly what you could not confirm."})
        start = len(emitted)
        gen = _one_round(base, model, messages, options, allow_tools, emitted, backend, user_text)
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
            break
        if not calls and allow_tools and nudges < 2:
            nudge = tools.follow_through("".join(emitted[start:]), user_text, box)
            if nudge:
                nudges += 1
                messages.append({"role": "assistant", "content": "".join(emitted[start:])})
                messages.append({"role": "system", "content": nudge})
                if emitted and not emitted[-1].endswith("\n"):
                    emitted.append("\n")
                    yield "text", "\n"
                continue
        if calls:
            steps += 1
            _record_calls(messages, "".join(emitted[start:]), calls, backend)
            for call in calls:
                yield "status", _status_line(call["name"], call["arguments"])
                result = box.call(call["name"], call["arguments"])
                _record_result(messages, call, result, backend)
            continue
        break

    # Never end on nothing. gpt-oss-20b searched ten times in the shootout, ran
    # out of steps and came back empty; the phone got status lines and a
    # sources footer and no answer. One last round without tools, told to
    # write up what it found; a plain statement if even that is empty.
    if not "".join(emitted).strip() and box.log:
        messages.append({"role": "system", "content":
                         "Stop using tools. Write your answer now, in plain words, from the tool results "
                         "above. If they did not settle it, say what you found and what you could not "
                         "confirm."})
        gen = _one_round(base, model, messages, options, False, emitted, backend, user_text)
        while True:
            try:
                piece = next(gen)
            except StopIteration:
                break
            yield "text", piece
    if not "".join(emitted).strip():
        yield "text", ("I looked into this but could not put together an answer I can stand behind. "
                       "Ask me again, or narrow the question.")
        emitted.append("(no answer)")

    reply = "".join(emitted)
    tail = tools.honesty_notes(reply, box, user_text) + tools.sources_footer(box, reply)
    if tail:
        yield "text", tail
