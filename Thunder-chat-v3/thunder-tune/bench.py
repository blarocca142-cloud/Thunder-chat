#!/usr/bin/env python3
"""Measure what Thunder's hardware actually delivers. Run before and after
`tune.sh apply` and compare - a tuning that is not measured is a guess.

    python3 bench.py                       # current THUNDER_MODEL, or thunder:latest
    python3 bench.py --model qwen3-coder --ctx 32768 --parallel 4

Reports generation tokens/sec, prompt-processing tokens/sec, time to first
token, peak VRAM and GPU temperature/throttling while it ran, and (with
--parallel) the throughput when several requests arrive at once - which is
what Forge does.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
PROMPT = ("Write a Python function that parses an ISO 8601 duration like P3DT4H5M "
          "into total seconds, with docstring and five doctest examples.")
LONG = "Summarise the following in three bullet points.\n\n" + (
    "Thunder is a private AI running on a home fleet of five machines. " * 400)


def gpu() -> dict:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,temperature.gpu,power.draw,"
                              "clocks_throttle_reasons.active", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        mem, temp, power, throttle = [x.strip() for x in out.split(",")]
        return {"vram_mb": int(mem), "temp_c": int(temp), "watts": float(power), "throttle": throttle}
    except Exception:
        return {}


def run(model: str, prompt: str, ctx: int, predict: int = 400) -> dict:
    body = {"model": model, "prompt": prompt, "stream": False,
            "options": {"num_ctx": ctx, "num_predict": predict, "temperature": 0}}
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        res = json.loads(r.read())
    res["wall"] = time.time() - t
    return res


def rate(n, ns):
    return n / (ns / 1e9) if ns else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("THUNDER_MODEL", "thunder:latest"))
    ap.add_argument("--ctx", type=int, default=16384)
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()

    peak = {"vram_mb": 0, "temp_c": 0, "throttle": set()}
    stop = threading.Event()

    def watch():
        while not stop.is_set():
            g = gpu()
            if g:
                peak["vram_mb"] = max(peak["vram_mb"], g["vram_mb"])
                peak["temp_c"] = max(peak["temp_c"], g["temp_c"])
                peak["throttle"].add(g["throttle"])
            time.sleep(0.5)

    threading.Thread(target=watch, daemon=True).start()
    print(f"model {a.model}, context {a.ctx}")
    run(a.model, "hi", a.ctx, 1)  # load it; load time is not what we measure
    r = run(a.model, PROMPT, a.ctx)
    print(f"  generation     {rate(r['eval_count'], r['eval_duration']):6.1f} tok/s")
    first = (r.get("load_duration", 0) + r.get("prompt_eval_duration", 0)) / 1e9
    print(f"  first token    {first:6.2f} s")
    r = run(a.model, LONG, a.ctx, 60)
    print(f"  prompt reading {rate(r['prompt_eval_count'], r['prompt_eval_duration']):6.0f} tok/s "
          f"({r['prompt_eval_count']} tokens)")
    if a.parallel > 1:
        t = time.time()
        with ThreadPoolExecutor(a.parallel) as pool:
            rs = list(pool.map(lambda _: run(a.model, PROMPT, a.ctx, 200), range(a.parallel)))
        total = sum(x["eval_count"] for x in rs)
        print(f"  {a.parallel} at once      {total / (time.time() - t):6.1f} tok/s combined")
    stop.set()
    thr = sorted(peak["throttle"] - {"0x0000000000000000", ""})
    print(f"  peak VRAM      {peak['vram_mb']} MB, peak temp {peak['temp_c']} C, "
          f"throttle {'none' if not thr else ', '.join(thr)}")


if __name__ == "__main__":
    main()
