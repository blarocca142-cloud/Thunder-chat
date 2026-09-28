#!/usr/bin/env python3
"""Thunder Deep: plan how to spread a mixture-of-experts model over the fleet.

A dense model split across machines is slow because every layer's weights
must be read by whoever holds them, and the towers read RAM ~40x slower than
the 3090 (measured: 55.5 -> 1.8 tok/s, commit 8dc686a). A mixture-of-experts
model changes the arithmetic: gpt-oss-120b has ~117B parameters but uses ~5B
per token. Attention and the shared parts - the bits every token needs - go
on the 3090. The experts, which are most of the size and read only a few at a
time, are spread across the RAM of Main, serverus and thunder-engine, each
node computing its own experts locally so only small activations cross the
network.

This script reads the model's layout and each node's free RAM and writes the
exact llama-server command: which layers' experts live where. It does not
start anything.

    python3 deep_plan.py --model /path/gpt-oss-120b.gguf --nodes serverus,thunder-engine
"""
from __future__ import annotations

import argparse
import re
import shlex
import struct
import subprocess
from pathlib import Path

NODE_IP = {"serverus": "10.168.168.13", "thunder-engine": "10.168.168.12",
           "thunder-cache": "10.168.168.11", "odris": "10.168.168.15"}
RPC_PORT = 50052
HEADROOM_GB = 3.0          # left free on each node for its own work
MAIN_RAM_FOR_EXPERTS = 14  # GB of Main's 32 that can hold experts beside the OS/API


def gguf_expert_bytes(path: Path) -> dict[int, int]:
    """Bytes of expert tensors per layer, read from the GGUF header."""
    types = {0: 4, 1: 2, 2: 18 / 32, 3: 20 / 32, 6: 22 / 32, 7: 24 / 32, 8: 34 / 32, 10: 84 / 256,
             11: 110 / 256, 12: 144 / 256, 13: 176 / 256, 14: 210 / 256, 15: 292 / 256, 30: 2,
             39: 17 / 32}  # bytes per element by ggml type; 39 = MXFP4
    with path.open("rb") as f:
        def rd(fmt):
            return struct.unpack("<" + fmt, f.read(struct.calcsize("<" + fmt)))[0]

        def rstr():
            return f.read(rd("Q")).decode("utf-8", "replace")

        def skip_val(t):
            sizes = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
            if t == 8:
                rstr()
            elif t == 9:
                et, n = rd("I"), rd("Q")
                for _ in range(n):
                    skip_val(et)
            else:
                f.read(sizes[t])

        assert f.read(4) == b"GGUF", "not a GGUF file"
        rd("I")
        n_tensors, n_kv = rd("Q"), rd("Q")
        for _ in range(n_kv):
            rstr()
            skip_val(rd("I"))
        per_layer: dict[int, int] = {}
        for _ in range(n_tensors):
            name = rstr()
            dims = [rd("Q") for _ in range(rd("I"))]
            gtype = rd("I")
            rd("Q")
            m = re.match(r"blk\.(\d+)\.ffn_.*_exps", name)
            if m:
                n = 1
                for d in dims:
                    n *= d
                per_layer[int(m.group(1))] = per_layer.get(int(m.group(1)), 0) + int(n * types.get(gtype, 1))
    return per_layer


def free_gb(node: str) -> float:
    out = subprocess.run(["ssh", "-o", "ConnectTimeout=5", node, "awk '/MemAvailable/{print $2}' /proc/meminfo"],
                         capture_output=True, text=True, timeout=15).stdout.strip()
    return int(out) / 1024 / 1024 if out else 0.0


def plan(layers: dict[int, int], capacity: list[tuple[str, float]]) -> dict[str, list[int]]:
    """Fill each place in order with whole layers of experts."""
    out: dict[str, list[int]] = {name: [] for name, _ in capacity}
    order = sorted(layers)
    i = 0
    for name, gb in capacity:
        room = gb * 1024 ** 3
        while i < len(order) and layers[order[i]] <= room:
            room -= layers[order[i]]
            out[name].append(order[i])
            i += 1
    if i < len(order):
        raise SystemExit(f"not enough RAM in the fleet: {len(order) - i} layers of experts left over "
                         f"({sum(layers[x] for x in order[i:]) / 1024 ** 3:.1f} GB)")
    return out


def layer_regex(ids: list[int]) -> str:
    return r"blk\.(" + "|".join(str(i) for i in ids) + r")\.ffn_.*_exps\."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--nodes", default="serverus,thunder-engine")
    ap.add_argument("--ctx", type=int, default=16384)
    a = ap.parse_args()

    layers = gguf_expert_bytes(a.model)
    total = sum(layers.values()) / 1024 ** 3
    print(f"{a.model.name}: {len(layers)} layers of experts, {total:.1f} GB")
    nodes = [n.strip() for n in a.nodes.split(",") if n.strip()]
    capacity = [("main", MAIN_RAM_FOR_EXPERTS)]
    for n in nodes:
        g = max(0.0, free_gb(n) - HEADROOM_GB)
        print(f"  {n}: {g:.1f} GB usable")
        capacity.append((n, g))
    placement = plan(layers, capacity)
    rpc = ",".join(f"{NODE_IP[n]}:{RPC_PORT}" for n in nodes if placement.get(n))
    cmd = ["llama-server", "-m", str(a.model), "--jinja", "-ngl", "99", "-c", str(a.ctx),
           "-fa", "on", "--host", "127.0.0.1", "--port", "8082"]
    if rpc:
        cmd += ["--rpc", rpc]
    for n in nodes:
        if placement.get(n):
            cmd += ["-ot", f"{layer_regex(placement[n])}=RPC[{NODE_IP[n]}:{RPC_PORT}]"]
    if placement["main"]:
        cmd += ["-ot", f"{layer_regex(placement['main'])}=CPU"]
    for name, ids in placement.items():
        print(f"  experts for layers {ids[0] if ids else '-'}..{ids[-1] if ids else '-'} -> {name} ({len(ids)})")
    print("\nOn each node (bound to its LAN address, firewalled to Main only - rpc-server has no auth):")
    for n in nodes:
        if placement.get(n):
            print(f"  ssh {n} 'rpc-server -H {NODE_IP[n]} -p {RPC_PORT}'")
    print("\nOn Main:\n  " + " ".join(shlex.quote(c) for c in cmd))


if __name__ == "__main__":
    main()
