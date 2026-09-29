#!/usr/bin/env python3
"""Checks for gpu_state(), the /status "gpu" block.

The bug being fixed: gpu.up asked thunder-genai on :9010, a service that was
stopped and disabled on 2026-09-29, so the phone was told the GPU was down
while it was serving every reply. The tests that matter are therefore about
*where the answer comes from* - Ollama and nvidia-smi, not :9010 - and about
the key set, because Android parses this object and those keys never change.

Run:

    python3 test_gpu_state.py
"""
import json
import urllib.request
from contextlib import contextmanager

import app

PASS, FAIL = 0, 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok    {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{('  -> ' + extra) if extra else ''}")


class _Resp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@contextmanager
def fake(util, ps_payload, ps_raises=False):
    """Pretend nvidia-smi printed `util` and Ollama answered `ps_payload`."""
    real_run, real_open = app._run, urllib.request.urlopen

    def _run(cmd, timeout=5):
        if cmd and cmd[0] == "nvidia-smi":
            return "" if util is None else f"{util}\n"
        return real_run(cmd, timeout=timeout)

    def _open(req, *a, **kw):
        url = req if isinstance(req, str) else req.full_url
        if "/api/ps" in url:
            if ps_raises:
                raise OSError("connection refused")
            return _Resp(ps_payload)
        return real_open(req, *a, **kw)

    app._run, urllib.request.urlopen = _run, _open
    try:
        yield
    finally:
        app._run, urllib.request.urlopen = real_run, real_open


LOADED = {"models": [{"name": "thunder-gptoss:latest"}]}


def main() -> int:
    # The whole point of the fix: a reachable Ollama plus a visible card is up,
    # regardless of what :9010 (thunder-genai) is doing.
    with fake(0, LOADED):
        s = app.gpu_state()
    check("up when Ollama answers and the card is visible", s["up"] is True, repr(s))
    check("loaded lists the resident model", s["loaded"] == ["thunder-gptoss:latest"], repr(s))
    check("idle card is not busy", s["busy"] is False, repr(s))

    # Android reads exactly these; a missing key silently becomes a default and
    # the UI lies rather than erroring, so absence has to be caught here.
    for k in ("up", "loaded", "loading", "busy", "progress"):
        check(f"key {k!r} present", k in s, repr(s))
    check("progress keeps step/total", s["progress"] == {"step": 0, "total": 0}, repr(s))
    check("progress never reports fake steps",
          s["progress"]["total"] == 0, "hasProgress() would draw a bar that cannot move")

    # Either half failing means the card cannot be promised to serve a reply.
    with fake(0, None, ps_raises=True):
        s = app.gpu_state()
    check("down when Ollama is unreachable", s["up"] is False, repr(s))
    check("no models claimed when Ollama is unreachable", s["loaded"] == [], repr(s))
    check("still has progress when down", s["progress"] == {"step": 0, "total": 0}, repr(s))

    with fake(None, LOADED):
        s = app.gpu_state()
    check("down when nvidia-smi says nothing", s["up"] is False, repr(s))
    check("not busy when utilisation is unknown", s["busy"] is False, repr(s))

    # Busy is what makes the phone show a spinner instead of dead air.
    with fake(97, LOADED):
        s = app.gpu_state()
    check("busy while the card is working", s["busy"] is True, repr(s))
    with fake(app.GPU_BUSY_UTIL_PCT, LOADED):
        check("busy at exactly the threshold", app.gpu_state()["busy"] is True)
    with fake(app.GPU_BUSY_UTIL_PCT - 1, LOADED):
        check("not busy just below the threshold", app.gpu_state()["busy"] is False)

    # An empty card is still a working card - up is about being able to serve.
    with fake(0, {"models": []}):
        s = app.gpu_state()
    check("up with nothing loaded", s["up"] is True, repr(s))
    check("loaded is empty, not null", s["loaded"] == [], repr(s))

    # /api/ps has used both spellings across Ollama versions.
    with fake(0, {"models": [{"model": "thunder-gptoss:latest"}]}):
        check("accepts 'model' as well as 'name'",
              app.gpu_state()["loaded"] == ["thunder-gptoss:latest"])
    with fake(0, {"models": [{"name": ""}, {"name": "x"}]}):
        check("drops nameless entries", app.gpu_state()["loaded"] == ["x"])

    # gpu_state must not be genai_state: that was the bug.
    with fake(0, LOADED):
        check("gpu_state does not depend on thunder-genai",
              app.gpu_state()["up"] is True and app.genai_state()["up"] is False,
              "genai is disabled, yet the GPU is up - the case that was broken")

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
