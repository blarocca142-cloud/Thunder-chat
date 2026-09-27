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
