# Ollama tuning, num_ctx audit, 11434 lockdown, /status GPU fix — 2026-09-29

Six items, from an overnight A/B suggestion. Four are done and verified. Two
could not be applied from this session because writing systemd units and
changing iptables were both refused by the sandbox — those two are written,
reviewed and ready to run, and the exact commands are at the bottom.

The headline is not the tuning. It is that **two of the six items were based on
assumptions that turned out to be false**, and a third turned up a latent bug
that had nothing to do with the request. Details below, honestly.

---

## Summary

| # | Item | Status |
|---|---|---|
| 1 | Flash attention + q8_0 KV drop-in | **Not applied** — blocked. Also: flash attention was *already on* |
| 2 | `num_ctx` on every chat request | **Done**, 7 call sites fixed |
| 3 | Firewall 11434 | **Not applied** — blocked. Allowlist corrected: cache (.11) is a real user |
| 4 | Rebuild with stock chat template | **No rebuild needed** — already stock. But the *recipe* in the repo was wrong |
| 5 | `/status` `gpu.up` | **Done**, verified live, 23 tests |
| 6 | Monitor on the 3090 | **Answered** — leave the cable alone, it costs 94 MiB |

Test suites: 271 checks, all passing.

---

## 1. Ollama env — flash attention was already on

**What the A/B suggestion assumed:** flash attention was off and turning it on
would speed things up.

**What is actually true.** Ollama 0.33.3 starts every runner with
`--flash-attn auto`, and `auto` resolves to *on*. From the journal, on every
model load without exception:

    llama_context: flash_attn            = auto
    resolve_fused_ops: Flash Attention enabled

Setting `OLLAMA_FLASH_ATTENTION=1` changes `auto` to a forced `on`. It does not
enable anything that was not already enabled. **There is no speed to gain here
because it is already being had.**

**q8_0 KV cache is real but small.** gpt-oss 20B uses interleaved sliding-window
attention — only 12 KV layers at head dim 64 — so the KV cache is far smaller
than a dense model's. Measured at 16384 context:

    llama_kv_cache: size = 384.00 MiB (16384 cells, 12 layers), K (f16): 192.00 MiB, V (f16): 192.00 MiB
    llama_kv_cache: size =  30.00 MiB ( 1280 cells, 12 layers), K (f16):  15.00 MiB, V (f16):  15.00 MiB

414 MiB total. Going to q8_0 roughly halves it — a saving of about **200 MiB out
of 24576**, or 0.8% of the card. It buys a little context headroom. It does not
buy tokens per second, and quantised KV can cost a little output quality.

### Baseline (the "before", and currently also the "after")

Fixed prompt, 400 tokens generated, 3 runs after a warm-up, `thunder-gptoss` at
16384 ctx:

| metric | value |
|---|---|
| generation | **201.41 tok/s** mean (200.26 / 201.44 / 202.54) |
| prompt eval | ~5160 tok/s |
| VRAM, Ollama runners | 12516 MiB (gpt-oss 11896 + nomic-embed 620) |
| VRAM, whole card | 13996 MiB of 24576 |

201 tok/s is not a typo and not a regression from the 55.5 tok/s in CLAUDE.md —
that figure was the *dense* 24B. gpt-oss 20B is a mixture-of-experts model with
roughly 3.6B parameters active per token, which is why it is about 3.6x faster
than a model nominally larger by only 20%.

There is no after-number because the drop-in could not be installed. Re-run
`/tmp/bench_ollama.py` after installing it; expect VRAM down ~200 MiB and tok/s
unchanged or very slightly down.

**Nothing about Ollama's configuration was changed. It was never restarted.**

---

## 2. `num_ctx` on every request — done

Ollama keys a loaded runner by model *and* context size. A request asking for a
different `num_ctx` than the resident runner does not just get a different
window — it **evicts the model and reloads it**, which is ~10 seconds of dead
air on a 12 GB model. Several call sites were sending no `num_ctx` at all.

It happened to be harmless *today* only because the Modelfile default is also
16384. The first time `THUNDER_NUM_CTX` was ever changed, the whole thing would
have started thrashing: chat loads at the new value, the nightly job reloads at
16384, the morning's first message reloads it back.

`NUM_CTX` is now defined once in `app.py` and read from `THUNDER_NUM_CTX` by
each standalone script.

| File | Call | Before | Now |
|---|---|---|---|
| `app.py:~636` | `classify_search_query` | **no options at all** | `num_ctx` |
| `app.py:~1319` | `warm_model` | **no options** | `num_ctx` |
| `app.py:~820` | `ollama_vision` | no `num_ctx` | `VISION_NUM_CTX` (8192) |
| `app.py:~1299` | `release_chat_model` | no options | **left alone, deliberately** |
| `app.py` ×3 | `ollama_chat`, `ollama_chat_stream`, Odris chat | `CHAT_OPTIONS` | now via `NUM_CTX` |
| `app.py` | tool/agent path | `TOOL_OPTIONS` | now via `NUM_CTX` |
| `forge.py:44` | `_chat` | **missing** | `num_ctx` |
| `consolidate.py:140` | `ask_model` | **missing** | `num_ctx` |
| `thunder-claims/extract.py:74` | `extract` | **missing** | `num_ctx` |
| `memory.py:113` | embeddings | — | **excluded on purpose** |
| `agent.py:71` | `_stream_ollama` | inherits caller's | already correct |

Three judgement calls, since they were asked for explicitly:

- **`warm_model` was the worst one.** It is the call that *loads* the model, and
  it sent no `num_ctx` — so it loaded the runner at the Modelfile default, and
  the first real chat request then threw that away and loaded it again.
  Warming the model was capable of costing time rather than saving it.
- **Vision gets its own 8192, not the chat model's 16384.** `thunder-vision` is
  a separate 3.3 GB model on its own runner, so it physically cannot evict the
  chat model. Forcing 16384 on it would just waste VRAM on a model that never
  sees a long conversation; leaving it unset would let it drift on a default.
- **`release_chat_model` deliberately gets nothing.** It sends `keep_alive: 0`,
  which *unloads* the runner. There is no context to size, and sending one
  risks loading the model in order to immediately discard it.

Verified live: after restarting thunder-main and running a chat request, the ICD
check and a web search, `journalctl -u ollama` shows **zero** `starting
llama-server` lines — no evictions, no reloads. `ollama ps` still reports
`thunder-gptoss` at 16384 and `nomic-embed-text` on its own untouched 2048.

---

## 3. Port 11434 — **the allowlist as specified would have broken the batch worker**

Ollama has no authentication of any kind. `ss -tlnp` confirms it listens on
`*:11434` — the v6 wildcard, so it accepts v4-mapped connections too, which
means an IPv4-only rule would have been decorative. Nothing in `INPUT`
restricted it; policy is `ACCEPT` with no rules.

The request was to allow localhost and odris (.15) and drop everyone else, then
verify thunder-cache (.11) is blocked. **thunder-cache must not be blocked.**

- `/home/blayne-cache/cache_worker.py:19` → `OLLAMA = "http://10.168.168.10:11434"`
- `thunder-cache.service` is **active and enabled**, running since 23 Sep.
- Its own docstring: *"sends the prompt to Main's Ollama for a real completion
  (Cache has no GPU of its own)"*.
- This is the overnight batch coding worker — the thing CLAUDE.md lists under
  "Also wanted".
- And `net-lockdown/lock.sh` already says it in its header: *"Cache and other
  nodes call Main's Ollama directly, so this is not just loopback-only."*

Blocking .11 would have broken it silently — no error on Main, jobs just never
completing — and the verification step would have *passed* while doing it. The
brief did say "plus any other genuine user you find", so the allowlist is
**localhost + .15 + .11**, and the verification expectation for cache is
inverted: it should succeed.

Checked and deliberately excluded: serverus (.13) and thunder-engine (.12) have
no reference to Main's Ollama anywhere. `memory.py:45` points *Main* at
serverus for embeddings — outbound from Main, so it needs nothing inbound.

Written, not run: `thunder-main-api/net-lockdown/port-11434.sh` (and
`unlock-11434.sh`). It uses a dedicated `THUNDER-OLLAMA-IN` chain so it is
re-runnable and cannot disturb the OUTPUT egress rules, covers v4 and v6, and
persists with `netfilter-persistent save` — the same mechanism `lock.sh`
already uses, confirmed by `/etc/iptables/rules.v4` and an enabled
`netfilter-persistent.service`.

---

## 4. Chat template — already stock; the *recipe* was the problem

No rebuild was needed, and none was done:

- `thunder-gptoss` and `shootout-gptoss20b` are **the same blob**,
  `sha256-27cd6c43…`, and the same model ID `761d8b958b11`.
- Their templates are byte-identical: 16738 bytes, both `sha256 a4c9919c…`.
- Parameters are `num_ctx 16384` and `temperature 0.6`, and there is **no baked
  SYSTEM block** — exactly as intended.

So the live model was already right and was left completely alone.

**But `thunder-main-api/thunder-gptoss-modelfile` was not.** It carried:

    TEMPLATE {{ .Prompt }}

That is a bare passthrough — one flat string, no roles, no tool block. It had
never reached the running model, so the recipe and the model had quietly
diverged and only the recipe was wrong. Anyone rebuilding from that file would
have gotten a model with the harmony format stripped out and **every tool call
broken**, with no obvious cause. The `TEMPLATE` line is now removed so the
build inherits the base model's template, which is what is actually running.

Tool calling verified end to end against the live model:

- ICD trap — `[checking the official code list: Z9Q.47]` → *"Z9Q.47 is not in the
  official 2026 ICD-10-CM list, so it is not a valid code."* It also declined to
  name a substitute code it could not verify.
- Web search — `[searching the web: …]` → `[reading https://en.wikipedia.org/…]`
  → answered with the source listed.

---

## 5. `/status` `gpu.up` — done

`genai_state()` asked thunder-genai on :9010, which was stopped and disabled
earlier today, so `gpu.up` had been stuck false ever since: the phone was being
told the card was down while it was serving every reply.

New `gpu_state()` reports the real GPU — `up` = nvidia-smi sees the card **and**
Ollama answers `/api/ps`; `loaded` = the model names Ollama reports; `busy` =
GPU utilisation ≥ 25%. One subprocess and one localhost call, both short
timeouts, since this is on the `/status` path.

Every key Android parses is unchanged (`ThunderApi.kt` `GpuState`:
`up`/`loading`/`busy`/`progress{step,total}`). `progress` stays `{0, 0}` on
purpose — it existed for diffusion's step counter and token generation has no
equivalent total, so `hasProgress()` stays false and the UI shows a plain
spinner instead of a bar that cannot move.

`genai_state()` is kept, unchanged, for `/system`'s `generators` key — that key
really is about thunder-genai, and reporting it as down is correct.

Live, after restart:

    "gpu": {"up": true,
            "loaded": ["nomic-embed-text:latest", "thunder-gptoss:latest"],
            "loading": null, "busy": false,
            "progress": {"step": 0, "total": 0}}

`test_gpu_state.py` — 23 checks, including that `gpu_state()` is up at the same
moment `genai_state()` is down, which is the exact case that was broken.

---

## 6. Monitor on the 3090 — leave it alone

**Do not move the cable. It would save 94 MiB.**

| process | VRAM |
|---|---|
| gnome-shell | 82 MiB |
| Xwayland | 6 MiB |
| snapd-desktop-integration | 6 MiB |
| **display total** | **94 MiB** (0.4% of the card) |

For scale, the TTS process is using 1328 MiB — fourteen times the display.

`display_active: Enabled`, monitor on `card1-HDMI-A-1`.

**And the iGPU is not available anyway.** `lspci` lists exactly one VGA device,
the RTX 3090. The i7-4790 does have Intel HD 4600, but it is not present on the
PCI bus at all and no `i915` module is loaded — the Lenovo Q87 board has it
disabled in BIOS, which is that board's default with a discrete card fitted. So
moving the cable would mean a BIOS trip to enable the iGPU, a driver, and a
display-manager change, all to recover 94 MiB.

Not worth it. If VRAM ever gets tight, evicting `nomic-embed-text` (620 MiB) or
moving TTS off the card (1328 MiB) are each worth more than ten times the
monitor.

---

## Rollback

**Nothing that runs was reconfigured**, so there is little to roll back. Ollama
was never restarted and its config is untouched; no model was rebuilt, deleted
or changed; no firewall rule was added.

Before-state saved to `/home/blayne/thunder-rollback-2026-09-29/`:
`ollama.unit.before.txt`, `rules.v4.before`, `rules.v6.before`.

- **Code (items 2, 4, 5):** `git revert` the commit, then
  `sudo systemctl restart thunder-main thunder-main-tls`.
- **`/status` only:** in `read_status()`, point the `"gpu"` probe back at
  `genai_state` instead of `gpu_state`.
- **Ollama drop-in**, if installed later:
  `sudo rm /etc/systemd/system/ollama.service.d/tuning.conf && sudo systemctl daemon-reload && sudo systemctl restart ollama`.
  `override.conf` is a separate file and is not touched either way.
- **Firewall**, if applied later: `sudo bash net-lockdown/unlock-11434.sh`.

## The two commands still to run

Both were refused by this session's sandbox, not by Main. Blayne (or a session
with permission) can run them as-is:

    cd ~/Thunder-chat/Thunder-chat-v3/thunder-main-api
    sudo cp ollama-tuning.conf /etc/systemd/system/ollama.service.d/tuning.conf
    sudo systemctl daemon-reload && sudo systemctl restart ollama

    sudo bash net-lockdown/port-11434.sh

After the first, confirm the runner picked it up — `--cache-type-k q8_0` should
appear in the command line, and if Ollama falls back for this architecture it
will simply be absent:

    pgrep -af llama-server
    journalctl -u ollama -n 50 | grep -i "kv cache\|flash"
    python3 /tmp/bench_ollama.py "after" 3

Restarting Ollama drops both resident models; `POST /warm` puts the chat model
back, or the next message will.

---

# Applied 2026-09-29

Blayne ran both of the commands above on thunder-main. Everything below was
measured afterwards; nothing was changed in this pass except `POST /warm`.

| # | Check | Result |
|---|---|---|
| 1 | Ollama env + active | **Pass** |
| 2 | q8_0 KV actually in use | **Pass** — not a fallback |
| 3 | Benchmark vs 201.41 baseline | **Pass, with a caveat** — 5.6% slower |
| 4 | Firewall, all four reachability checks | **Pass** |
| 5 | `gpu.up` true, Thunder answering | **Pass** |

## 1. Environment

`systemctl is-active ollama` → `active`. `systemctl show ollama -p Environment`
carries all four variables, so the drop-in appended rather than replaced:

    OLLAMA_KEEP_ALIVE=-1  OLLAMA_HOST=0.0.0.0:11434
    OLLAMA_FLASH_ATTENTION=1  OLLAMA_KV_CACHE_TYPE=q8_0

## 2. q8_0 KV is real, not a fallback

The runner command line proves it — this is the thing that would simply be
absent if Ollama had refused the setting for this architecture:

    llama-server ... -c 16384 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on

And the allocation halved, as predicted:

    llama_kv_cache: size = 204.00 MiB (16384 cells, 12 layers), K (q8_0): 102.00 MiB, V (q8_0): 102.00 MiB
    llama_kv_cache: size =  15.94 MiB ( 1280 cells, 12 layers), K (q8_0):   7.97 MiB, V (q8_0):   7.97 MiB

**414.00 MiB → 219.94 MiB**, a saving of 194 MiB. Flash attention now logs
`flash_attn = enabled` instead of `auto` — the same resolved state, forced.

### VRAM, like for like

Compared with both models resident, as in the baseline:

| | before | after | delta |
|---|---|---|---|
| gpt-oss runner | 11896 MiB | 11704 MiB | **−192 MiB** |
| runners (gpt-oss + nomic-embed) | 12516 MiB | 12324 MiB | −192 MiB |
| whole card | 13996 MiB | 13804 MiB | −192 MiB |

192 MiB of 24576 — **0.8% of the card**, exactly the predicted size. The 1328
MiB the TTS process holds is unrelated and unchanged.

## 3. Speed: q8_0 KV costs about 5.6%

Same `/tmp/bench_ollama.py`, same prompt, 400 tokens, 3 runs after a warm-up:

| | runs (tok/s) | mean |
|---|---|---|
| before (f16 KV) | 200.26 / 201.44 / 202.54 | **201.41** |
| after (q8_0 KV) | 190.84 / 189.50 / 190.03 | **190.12** |

**−11.3 tok/s, −5.6%.** The two sets do not overlap — the slowest "before" run
is 9.4 tok/s faster than the fastest "after" run — so this is a real effect and
not noise. Prompt eval is unchanged at ~5000 tok/s.

This is worth being plain about: **the prediction in this report was "tok/s
unchanged or very slightly down", and 5.6% is more than that.** Quantised KV
costs a dequantisation step on every attention read, and on a model whose KV
cache was already tiny there is no bandwidth saving to pay for it.

**What was actually bought: 192 MiB (0.8% of the card) for 5.6% of the speed.**
That is a bad trade on today's workload, where VRAM is not the constraint —
11 GB of 24 GB is in use. It is only worth keeping if context is about to grow
well past 16384. Undo is one command:

    sudo rm /etc/systemd/system/ollama.service.d/tuning.conf
    sudo systemctl daemon-reload && sudo systemctl restart ollama

`OLLAMA_FLASH_ATTENTION=1` is harmless either way — it forces what `auto`
already chose, and can stay.

Not a regression, though it appears in the same logs: `KV cache shifting is not
supported for this context, disabling KV cache shifting`. That line has been
present on every load since **Sep 27**, before any of this, and is a property of
gpt-oss's interleaved sliding-window attention, not of q8_0.

## 4. Firewall

`THUNDER-OLLAMA-IN` is installed on both v4 and v6, one reference each, from
`INPUT ... tcp dpt:11434`. v4 order: `lo`, `127.0.0.0/8`, `10.168.168.15`,
`10.168.168.11`, RELATED/ESTABLISHED, rate-limited LOG, DROP. The v6 chain is
`lo` / `::1` / RELATED,ESTABLISHED / DROP — its first rule is interface-scoped
to `lo`, checked with `-v`, so it is not a blanket accept.

All four checks behaved as intended:

| From | Expected | Result |
|---|---|---|
| localhost | works | `{"version":"0.33.3"}` |
| odris `.15` | works | `{"version":"0.33.3"}` |
| thunder-cache `.11` | **works** | `{"version":"0.33.3"}` |
| thunder-engine `.12` | times out | `URLError <urlopen error timed out>` |

Engine times out rather than being refused, which is the DROP doing its job —
a port scan gets silence, not a closed-port answer.

Cache reaching Ollama is the check that matters most: the allowlist in the
original brief would have blocked it and broken the overnight batch worker
silently. `thunder-cache.service` on `.11` is still `active (running)`, up
5 days. It does print `unit file ... changed on disk, run daemon-reload` — that
is pre-existing, unrelated to this work, and was left alone.

Persistence and blast radius both confirmed: `THUNDER-OLLAMA-IN` is in
`/etc/iptables/rules.v4` and `rules.v6` with all its rules,
`netfilter-persistent` is `enabled`, and the OUTPUT egress rules for uids 994
(`genai`) and 997 (`ollama`) are **all still present and counting packets** —
the dedicated chain did not disturb them.

*(Note for future sessions: the other nodes have no `curl`. Use
`ssh <node> python3 -c '...urllib...'` for reachability checks.)*

Undo: `sudo bash net-lockdown/unlock-11434.sh`.

## 5. Thunder is answering

`POST /warm` returns immediately and loads in the background; gpt-oss was
resident ~12s later. `/status` reports `gpu.up: true` with
`loaded: ["thunder-gptoss:latest"]` — the fix from item 5 holding up against a
real restart, which is the first time it has been tested that way.

A real `POST /chat`, asked what GPU it runs on and what its context window is:

> I'm running on the RTX 3090 in thunder-main.
> I'm not sure exactly what context window the gpt-oss 20B model is using right
> now — it's somewhere in the 30-k-token range, but I don't have a definitive
> number.

The GPU is right. The context window is **16384**, so "30-k-token range" is
wrong — but it flagged its own uncertainty rather than stating a number flatly,
which is the behaviour priority 4 asks for. The underlying gap is real and
worth fixing separately: **Thunder cannot see its own runtime configuration.**
`num_ctx` is a fact about the running process that nothing puts in front of the
model — a candidate for the profile block in memory, or for a fleet-status tool
under priority 2.

Across the whole verification `journalctl` shows exactly two
`starting llama-server` lines, for two different blobs (gpt-oss and
nomic-embed-text). **Zero reloads of an already-resident model** — the item 2
`num_ctx` work is still holding.

## Reverted — same day, 2026-09-29

Blayne made the call to back the `q8_0` KV drop-in out. The saving was real but
trivial and the cost was not: 192 MiB of 24576 (0.8% of the card) against a
5.6% drop in generation speed.

Removed with the documented undo:

    sudo rm /etc/systemd/system/ollama.service.d/tuning.conf
    sudo systemctl daemon-reload && sudo systemctl restart ollama

Verified on the live box afterwards:

- `/etc/systemd/system/ollama.service.d/` holds only `override.conf`.
  `systemctl show ollama -p Environment` has `OLLAMA_HOST` and
  `OLLAMA_KEEP_ALIVE` and **no** `OLLAMA_KV_CACHE_TYPE`. Service `active`.
- After `POST /warm`, the runner command line has **no** `--cache-type-k` or
  `--cache-type-v` flag. The journal allocates KV at f16 again: 384.00 MiB
  non-SWA + 30.00 MiB SWA = **414.00 MiB**, matching the pre-drop-in figure
  exactly. `resolve_fused_ops: Flash Attention enabled` still present with
  nothing setting `OLLAMA_FLASH_ATTENTION` — `--flash-attn auto` gets it right
  on its own, as recorded above.
- Benchmark, same script and prompt, 3 runs after warmup:

  | config | mean gen tok/s |
  |---|---|
  | f16 (before) | 201.41 |
  | q8_0 drop-in | 190.12 |
  | **f16 (reverted)** | **201.53** |

  201.53 against 201.41 is the same number inside run-to-run scatter. The
  revert restored full speed; nothing else moved. Runner VRAM 11884 MiB, GPU
  total 13358 MiB, model 100% GPU at 16384 context.
- Unrelated state still intact: `THUNDER-OLLAMA-IN` present on v4 and v6,
  odris (.15) and cache (.11) both read `{"version":"0.33.3"}` from
  `10.168.168.10:11434`, and thunder-engine (.12, not allowlisted) times out as
  designed. `/status` reports `gpu.up: true`, `state: ok`, and a real `POST
  /chat` answered correctly.

The drop-in file is kept at `thunder-main-api/ollama-tuning.conf` as a record of
what was measured. It is not deployed. Only revisit it if the context window
grows well past 16384, where the KV cache is large enough for the trade to
change sign.
