# thunder-tune

Software that makes Main's hardware work harder for Thunder. One command, one
command to undo, and a benchmark to prove each change earned its place.

    python3 bench.py            # before
    sudo ./tune.sh apply
    python3 bench.py            # after
    sudo ./tune.sh status
    sudo ./tune.sh revert       # exact undo

| | What | Why it helps Thunder |
|---|---|---|
| zram | 12GB of zstd-compressed swap in RAM, tried before the SSDs | Ordinary memory compresses 2-3x, so the 32GB board holds more before touching disk. Does not shrink model weights (already 4-bit). |
| Ollama | flash attention, 8-bit KV cache, 4 parallel, 2 models resident, 24h keep-alive | ~2x context in the same VRAM; Forge's candidates run at once; coding and medical models both stay loaded. |
| GPU | persistence mode, 300W limit, re-applied at boot | Decoding is memory-bound, so little speed is lost below 350W, and the GDDR6X - which throttles on heat - runs cooler. `bench.py` shows the trade; raise `GPU_WATTS` if it costs too much. |
| CPU/VM | performance governor, swappiness 150 | Kernel prefers cheap zram over dropping file cache. |

Needs sudo on Main. Not yet run on the hardware - run `bench.py` before and
after, and revert anything that does not pay.

Deliberately not here: CPU overclocking (the i7-4790 is multiplier-locked) and
GPU memory overclocking (needs an X server on a headless box, and the gain is
smaller than the heat cost on GDDR6X).

## Every other tower: node-tune.sh

    scp thunder-tune/node-tune.sh serverus:~ && ssh -t serverus 'sudo ./node-tune.sh apply'
    (same for thunder-cache, thunder-engine; Main can run it too for the network part)

zram at half the machine's RAM, performance governor, swappiness 150, and fq +
BBR with 16MB socket buffers for fleet traffic.

**Odris needs root first.** Its root password is lost, so nothing system-level
can change there. Recovering it takes a keyboard and monitor on Odris once:
reboot, hold Shift for GRUB, `e` on the boot entry, add `init=/bin/bash` to the
`linux` line, Ctrl+X, then `mount -o remount,rw /` and `passwd`. Until then,
Odris's speedups are the ones that need no root: the gate's RAM cache and
prefetch.

## Why not pool all the RAM

Measured on this fleet (commit 8dc686a): one 24B model split across machines
with llama.cpp RPC runs 55.5 tok/s on the 3090 alone, 2.97 with serverus, 1.80
with four machines. Gigabit is ~100x slower than RAM, and every added tower is
another hop. Each machine's RAM is used at full speed by giving it its own job
instead: Odris caches the internet, serverus holds memory, Main runs the model.

## Free tools worth getting

| Tool | What it buys | Cost |
|---|---|---|
| llama.cpp `llama-server` | Speculative decoding (small draft model + big model): 1.5-2x faster replies on dense models. Ollama cannot do it. | free |
| SearXNG on Odris | Real metasearch across many engines instead of scraping DuckDuckGo Lite. Better search = fewer wrong answers. | free |
| Tailscale | Thunder from anywhere - the app on 5G reaches Main over an encrypted WireGuard link. | free (personal) |
| smartmontools | Drive failure warnings before a drive dies; the fleet has no SMART at all. | free |
| Unsloth | Fine-tuning the chosen model to be Thunder (QLoRA on the 3090). | free |
| Jellyfin | The home theater. | free |

Only purchase worth considering under $100: thermal pads for the 3090's memory
(~$15-25), and only if bench.py shows memory-temperature throttling - GDDR6X on
3090s is known for it, and re-padding drops memory temps substantially.
