#!/usr/bin/env python3
"""How many people can chat with Thunder at the same time?

Sends N simultaneous streaming requests straight at Ollama, bypassing the API,
so what is measured is the model and the card rather than FastAPI. Uses the
same model tag and the same num_ctx production uses, because a smaller context
would make the numbers look better than the real thing.

Read-only: nothing is restarted, no config is touched, and no reply is written
to Thunder's memory or history.
"""

import json
import os
import statistics
import subprocess
import sys
import threading
import time
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("THUNDER_MODEL", "thunder-gptoss:latest")
NUM_CTX = int(os.environ.get("THUNDER_NUM_CTX", "16384"))

# Production's CHAT_OPTIONS (thunder-main-api/app.py), so the test pays the
# same context and length costs a real chat turn does.
OPTIONS = {
    "repeat_penalty": 1.18,
    "repeat_last_n": 256,
    "num_predict": 1400,
    "num_ctx": NUM_CTX,
}

QUESTION = ("Explain how a medical claim moves from the doctor's office to "
            "payment, in about 250 words.")


def ask(tag: str) -> dict:
    """One streaming turn. The tag is a distinct first line so that no two
    requests share a prompt - Ollama caches prefixes, and a cache hit would
    report a time to first token that no real user would ever see."""
    body = json.dumps({
        "model": MODEL,
        "stream": True,
        "messages": [{"role": "user", "content": f"[request {tag}]\n{QUESTION}"}],
        "options": OPTIONS,
    }).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})

    start = time.perf_counter()
    ttft = None
    final = {}
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            if ttft is None and msg.get("message", {}).get("content"):
                ttft = time.perf_counter() - start
            if msg.get("done"):
                final = msg
    total = time.perf_counter() - start

    eval_count = final.get("eval_count", 0)
    eval_ns = final.get("eval_duration", 0) or 1
    return {
        "tag": tag,
        "ttft": ttft if ttft is not None else total,
        "total": total,
        "eval_count": eval_count,
        "tok_s": eval_count / (eval_ns / 1e9),
    }


def gpu() -> str:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader"],
        capture_output=True, text=True)
    return out.stdout.strip()


def sample_gpu(stop: threading.Event, peak: list) -> None:
    while not stop.is_set():
        peak.append(gpu())
        stop.wait(1.0)


def run(n: int, watch_gpu: bool = False) -> dict:
    results: list[dict] = []
    lock = threading.Lock()

    def worker(i: int) -> None:
        try:
            r = ask(f"{n}-{i}-{int(time.time())}")
        except Exception as e:  # a failure at high N is itself a finding
            r = {"tag": f"{n}-{i}", "error": str(e), "ttft": float("nan"),
                 "total": float("nan"), "eval_count": 0, "tok_s": 0.0}
        with lock:
            results.append(r)

    samples: list = []
    stop = threading.Event()
    watcher = None
    if watch_gpu:
        watcher = threading.Thread(target=sample_gpu, args=(stop, samples))
        watcher.start()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    wall_start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - wall_start

    if watcher:
        stop.set()
        watcher.join()

    ok = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]
    tokens = sum(r["eval_count"] for r in ok)
    return {
        "n": n,
        "wall": wall,
        "avg_ttft": statistics.mean(r["ttft"] for r in ok) if ok else float("nan"),
        "max_ttft": max((r["ttft"] for r in ok), default=float("nan")),
        "avg_tok_s": statistics.mean(r["tok_s"] for r in ok) if ok else 0.0,
        # Throughput across everyone: all tokens produced divided by the wall
        # clock of the whole batch, which is what the card actually delivered.
        "total_tok_s": tokens / wall if wall else 0.0,
        "max_total": max((r["total"] for r in ok), default=float("nan")),
        "avg_total": statistics.mean(r["total"] for r in ok) if ok else float("nan"),
        "tokens": tokens,
        "errors": [r["error"] for r in errors],
        "gpu_samples": samples,
    }


def main() -> None:
    print(f"model={MODEL} num_ctx={NUM_CTX}")
    print(f"gpu before: {gpu()}")

    print("warm-up...", flush=True)
    w = ask("warmup")
    print(f"  warm-up: {w['total']:.1f}s, {w['eval_count']} tokens, "
          f"{w['tok_s']:.1f} tok/s\n", flush=True)

    rows = []
    for n in (1, 2, 4, 8):
        print(f"N={n} ...", flush=True)
        row = run(n, watch_gpu=(n == 8))
        rows.append(row)
        print(f"  avg ttft {row['avg_ttft']:.2f}s | slowest ttft {row['max_ttft']:.2f}s | "
              f"avg {row['avg_tok_s']:.1f} tok/s/user | {row['total_tok_s']:.1f} tok/s total | "
              f"slowest reply {row['max_total']:.1f}s | {row['tokens']} tokens", flush=True)
        if row["errors"]:
            print(f"  errors: {row['errors']}", flush=True)
        if row["gpu_samples"]:
            print(f"  gpu during run: {max(row['gpu_samples'])}", flush=True)

    print("\n| N | avg TTFT | slowest TTFT | avg tok/s per user | total tok/s | slowest reply |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['n']} | {r['avg_ttft']:.2f}s | {r['max_ttft']:.2f}s | "
              f"{r['avg_tok_s']:.1f} | {r['total_tok_s']:.1f} | {r['max_total']:.1f}s |")

    print(f"\ngpu after: {gpu()}")
    with open(os.environ.get("LOADTEST_JSON", "/tmp/thunder-loadtest/results.json"), "w") as f:
        json.dump(rows, f, indent=2)


if __name__ == "__main__":
    sys.exit(main())
