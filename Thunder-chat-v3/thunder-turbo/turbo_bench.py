#!/usr/bin/env python3
"""Turbo vs plain llama-server on prompts neither has seen: tokens/sec, draft
acceptance, and whether the output is identical (it must be).

Start the same target twice - PLAIN_PORT without a draft, TURBO_PORT with -
then run this. A warm-up uses a different prompt, because speculative decoding
that has already seen a prompt will replay it and report a fake speedup (that
happened while building this: 4.5x that was really 1.0x)."""
import json, urllib.request, sys
import os
port_plain = int(os.environ.get("PLAIN_PORT", "8083")); port_turbo = int(os.environ.get("TURBO_PORT", "8081"))
WARM = "Say hello in five words."
P = [("new code", "Write a Python function that merges overlapping intervals in a list of [start, end] pairs, with a docstring."),
     ("new code 2", "Write a Python class LRUCache with get and put methods using OrderedDict, with comments."),
     ("edit (repeats input)", "Here is code:\n\ndef area(w, h):\n    return w * h\n\ndef perimeter(w, h):\n    return 2 * (w + h)\n\ndef diagonal(w, h):\n    return (w ** 2 + h ** 2) ** 0.5\n\ndef scale(w, h, k):\n    return w * k, h * k\n\nRewrite all of it exactly, adding type hints (float) to every parameter and return."),
     ("prose", "Explain in two paragraphs why the sky is blue.")]
def go(port, prompt):
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": 300, "temperature": 0, "cache_prompt": False}
    r = urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=600)
    d = json.loads(r.read()); t = d.get("timings", {})
    return t.get("predicted_per_second", 0), t.get("draft_n", 0), t.get("draft_n_accepted", 0), d["choices"][0]["message"]["content"]
go(port_plain, WARM); go(port_turbo, WARM)
for name, p in P:
    a = go(port_plain, p); b = go(port_turbo, p)
    print(f"  {name:22s} plain {a[0]:5.1f} | turbo {b[0]:5.1f} tok/s ({b[0]/a[0]:.2f}x), accepted {b[2]}/{b[1]}, identical: {a[3] == b[3]}")
