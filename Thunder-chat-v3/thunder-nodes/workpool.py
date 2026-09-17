#!/usr/bin/env python3
"""Spread CPU work across the machines that are doing nothing.

thunder-cache, thunder-engine and serverus sit at 0.00 load with twenty cores
and eighty gigabytes of RAM between them. Meanwhile Main does OCR one page at a
time on the same box that is trying to generate video on the 3090.

This hands that work out. It is deliberately not a job queue with a database
and a scheduler - the fleet is five machines on one switch, and the honest
shape of the problem is "run these commands somewhere that is free".

**Capability detection, not configuration.** Each node is asked what it can
actually run, and work only goes where the tool exists. Today that means
tesseract and ffmpeg live on Main alone, so OCR does not move and this buys
nothing. The moment `sudo apt install tesseract-ocr` runs on a node, the next
batch uses it with no code change and nobody having to remember to say so -
the same way the drive health started working the hour smartmontools appeared.

Work is streamed over SSH: the file goes in on stdin, the result comes back on
stdout. Nothing is copied to the node and nothing is left there, so a node
disappearing mid-batch costs one retry and never leaves half a job behind.

    ./workpool.py                 what each machine can do
    ./workpool.py --bench         how long a page of OCR takes on each
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

NODES = ["thunder-cache", "thunder-engine", "serverus", "odris"]
TOOLS = ["tesseract", "ffmpeg", "pdftoppm", "rsync"]
CACHE = Path(os.path.expanduser("~")) / ".thunder_workpool.json"
CACHE_SECONDS = 1800


def _ssh(node: str, command: str, stdin: bytes | None = None,
         timeout: int = 300) -> tuple[bool, bytes, str]:
    try:
        r = subprocess.run(
            ["ssh", "-n" if stdin is None else "-T",
             "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", node, command],
            input=stdin, capture_output=True, timeout=timeout)
        return r.returncode == 0, r.stdout, r.stderr.decode(errors="replace")[-300:]
    except Exception as e:
        return False, b"", str(e)


def capabilities(refresh: bool = False) -> dict:
    """What each machine can run, cached because asking costs an SSH round trip.

    Main is included as a worker - it is usually the fastest box in the fleet,
    and the point is to stop it doing everything serially, not to leave it idle.
    """
    if not refresh and CACHE.is_file():
        try:
            cached = json.loads(CACHE.read_text())
            if time.time() - cached.get("at", 0) < CACHE_SECONDS:
                return cached["nodes"]
        except Exception:
            pass

    found = {"local": {
        "tools": [t for t in TOOLS if shutil.which(t)],
        "cores": os.cpu_count() or 2,
        "reachable": True,
    }}

    def probe(node: str) -> tuple[str, dict]:
        ok, out, _ = _ssh(
            node,
            "printf '%s ' " + " ".join(f"$(command -v {t} >/dev/null && echo {t})"
                                       for t in TOOLS) + "; nproc",
            timeout=20)
        if not ok:
            return node, {"tools": [], "cores": 0, "reachable": False}
        parts = out.decode(errors="replace").split()
        cores = int(parts[-1]) if parts and parts[-1].isdigit() else 1
        return node, {"tools": [p for p in parts[:-1] if p in TOOLS],
                      "cores": cores, "reachable": True}

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(NODES)) as pool:
        for node, info in pool.map(probe, NODES):
            found[node] = info

    CACHE.write_text(json.dumps({"at": time.time(), "nodes": found}, indent=2))
    return found


def workers_for(tool: str, caps: dict | None = None) -> list[tuple[str, int]]:
    """(node, slots) for every machine that can run this tool, best first.

    One slot per two cores rather than one per core: these jobs are disk and
    memory heavy as well as CPU heavy, and saturating every core on a box that
    is also serving something else is how "use the idle machines" turns into
    "make everything slow".
    """
    caps = caps or capabilities()
    out = []
    for node, info in caps.items():
        if info.get("reachable") and tool in info.get("tools", []):
            out.append((node, max(1, info.get("cores", 2) // 2)))
    # Local last: prefer to keep Main free for the GPU work it alone can do.
    out.sort(key=lambda p: (p[0] == "local", -p[1]))
    return out


def run_one(node: str, command: str, payload: bytes | None,
            timeout: int) -> tuple[bool, bytes, str]:
    if node == "local":
        try:
            r = subprocess.run(command, shell=True, input=payload,
                               capture_output=True, timeout=timeout)
            return r.returncode == 0, r.stdout, r.stderr.decode(errors="replace")[-300:]
        except Exception as e:
            return False, b"", str(e)
    return _ssh(node, command, payload, timeout)


def map_work(tool: str, items: list, command_for, payload_for,
             timeout: int = 300, on_result=None) -> dict:
    """Run one command per item, spread over every machine that has the tool.

    Falls back to local for anything that fails remotely, because a batch that
    half-finishes because a node rebooted is worse than a slow batch.
    """
    workers = workers_for(tool)
    if not workers:
        return {"error": f"nothing in the fleet has {tool}", "results": {}}

    # Interleaved, not grouped. Laying the slots out as [engine, engine,
    # engine, engine, cache, cache, ...] and then handing out item i to slot
    # i sends the first four items to the first machine and leaves the rest
    # idle - which is the exact problem this file exists to solve. Round-robin
    # across machines first, then depth.
    slots: list[str] = []
    remaining = {node: n for node, n in workers}
    while any(remaining.values()):
        for node, _ in workers:
            if remaining[node] > 0:
                slots.append(node)
                remaining[node] -= 1
    results, placement = {}, {}
    started = time.time()

    def do(index_item):
        i, item = index_item
        node = slots[i % len(slots)]
        ok, out, err = run_one(node, command_for(item), payload_for(item), timeout)
        if not ok and node != "local":
            # One retry, locally. Remote failure is usually the node, not the job.
            ok, out, err = run_one("local", command_for(item), payload_for(item), timeout)
            node = f"local (after {node} failed)"
        return item, node, ok, out, err

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(slots)) as pool:
        for item, node, ok, out, err in pool.map(do, enumerate(items)):
            results[str(item)] = {"ok": ok, "node": node, "error": None if ok else err}
            placement[node] = placement.get(node, 0) + 1
            if on_result:
                on_result(item, ok, out, err)

    return {
        "results": results,
        "placement": placement,
        "seconds": round(time.time() - started, 1),
        "workers": [f"{n} x{c}" for n, c in workers],
    }


def ocr_batch(images: list[Path], timeout: int = 180) -> dict[Path, str]:
    """OCR a pile of images wherever there is a free machine with tesseract.

    The image is streamed in on stdin and the text comes back on stdout, so
    nothing is written on the remote node and nothing has to be cleaned up.
    """
    text: dict[Path, str] = {}

    def keep(item, ok, out, err):
        text[item] = out.decode(errors="replace") if ok else ""

    report = map_work(
        "tesseract", images,
        command_for=lambda p: "tesseract - stdout --dpi 200 2>/dev/null",
        payload_for=lambda p: p.read_bytes(),
        timeout=timeout, on_result=keep)
    text["_report"] = report  # type: ignore[index]
    return text


def main() -> int:
    caps = capabilities(refresh=True)
    print(f"{'machine':16} {'cores':>5}  tools")
    for node, info in caps.items():
        if not info.get("reachable"):
            print(f"  {node:14} {'-':>5}  unreachable")
            continue
        print(f"  {node:14} {info['cores']:>5}  {', '.join(info['tools']) or '(none)'}")

    print("\nwork that can be spread right now:")
    for tool in ("tesseract", "ffmpeg", "pdftoppm"):
        w = workers_for(tool, caps)
        where = ", ".join(f"{n}" for n, _ in w) or "nowhere"
        slots = sum(c for _, c in w)
        print(f"  {tool:12} {slots:>2} slots   {where}")
        if [n for n, _ in w] == ["local"]:
            print(f"               ^ only Main. Install {tool} on a node and it "
                  f"joins automatically.")

    if "--bench" in sys.argv:
        img = next((p for p in Path("/tmp").rglob("*.jpg")), None)
        if not img:
            print("\nno sample image in /tmp to benchmark with")
            return 0
        print(f"\nOCR of {img.name} on each machine that can:")
        for node, _ in workers_for("tesseract", caps):
            t = time.time()
            ok, out, err = run_one(node, "tesseract - stdout --dpi 200 2>/dev/null",
                                   img.read_bytes(), 120)
            print(f"  {node:14} {'ok' if ok else 'FAILED':7} "
                  f"{time.time() - t:5.1f}s  {len(out)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
