# HANDOFF FOR CLAUDE — Thunder
Owner: Blayne (blarocca142-cloud). Solo. Family business context (see "Where this is going").
Repo: https://github.com/blarocca142-cloud/Thunder-chat
Use **Thunder-chat-v3 only**. Ignore v1 and v2.

Last substantially updated 2026-09-16. Read this before exploring — it exists so
you don't burn Blayne's usage rediscovering the fleet.

## Fleet

| Host | Address | Role | Notes |
|---|---|---|---|
| thunder-main | 10.168.168.10 | API, Ollama, generation | RTX 3090 24GB, 30GB RAM (maxed) |
| thunder-cache | .11 | **Jellyfin :8096** | i5-3470, 22GB. `thunder-nodes/cache/jellyfin/` |
| thunder-engine | .12 | safety yes/no (9002) | i7-3770, 30GB |
| serverus | .13 | memory (9001) | **Xeon E3-1230 v5** — best CPU in the fleet, barely used |
| odris | .15 | heartbeat 9003, websearch 9004, admin 9005, **TTS 9006**, health 9007, youtube 9008, **tool gate 9009** | Radeon 550 **4GB**, 30GB RAM. Code in `/home/blayne-odris/` |

SSH works to all of them from Main via the aliases in `~/.ssh/config`
(`odris`, `serverus`, `thunder-cache`, `thunder-engine`). **Use the aliases** —
raw IPs default to the wrong username and look like an auth failure.

Odris services are system units needing root Blayne doesn't have the password
for. **That is Odris only:** on thunder-main `blayne` has passwordless sudo
(`(ALL) NOPASSWD: ALL`, found 2026-09-28) - a standing security decision for
the box that will hold claims data. Deploy by copying the file and `pkill`ing the process — `Restart=always`
brings it back on the new code in 3s. The TTS service is a **systemd user**
unit, so `systemctl --user restart thunder-tts` works.
**Lingering was in fact OFF until 2026-09-29** (`/var/lib/systemd/linger/` was
empty; the user manager was alive only because Blayne was logged in at tty2) —
so the user units would not have come back after a reboot or a logout. It is
now on (`sudo loginctl enable-linger blayne`), which is what that claim always
assumed.

## What runs where

- **Main**: `thunder-main` (FastAPI :8080), `ollama` (:11434). `thunder-genai`
  is **stopped and disabled** as of 2026-09-29 — see below.
- **Thunder Claims on Main :8770 - https only** (2026-09-30). The office uses
  the **Thunder Claims Windows program** (`thunder-claims/desktop/`, Electron),
  not a browser: it trusts **only the Thunder fleet CA** (same `thunder_ca.crt`
  as the APK, fingerprint `5C:5A:88:...:7C:D0`, checked in CI), refuses every
  other origin, keeps nothing on the laptop (in-memory session), grants no
  permissions. Installer: GitHub release **`claims-desktop`**, asset
  `ThunderClaims-Setup.exe`, built on a Windows runner by
  `.github/workflows/build-claims-desktop.yml`. That release is published
  **`--latest=false` on purpose** - the phone updater reads "latest release"
  for `thunder.apk`; never let a desktop release become latest.
  Server: `thunder-claims/claims_web.py`, stdlib only, systemd **user** unit
  `thunder-claims-web` (`systemctl --user restart thunder-claims-web`, no sudo),
  unit kept in the repo. TLS with Main's fleet cert
  (`thunder-main-api/thunder-data/tls/server.{crt,key}`); it refuses to listen
  off loopback without TLS. **One login per person** in
  `~/.thunder/claims_users.json` (scrypt, mode 600): `python3 claims_web.py
  adduser <name>` (also `users`, `passwd`, `disable`, `enable`). Lockout after
  5 wrong tries (15 min), auto-logoff after 15 idle minutes, sessions in memory
  only. `access.log` in the vault dir records who/ip/path/status (ids only),
  and the vault audit credits the logged-in person. `test_claims_web.py` = 79
  checks, mostly attacks. **Synthetic patients only**; nothing is ever
  submitted to a payer. The UI mimics EZClaim on purpose - see
  `thunder-claims/EZCLAIM-LOOK.md` (EZClaim's videos studied frame by frame).
  **The office bills only Florida PIP** (13 offices; patients are never billed).
  `fl_pip.py` computes the Fla. Stat. 627.736 clocks on every claim, never
  stored: 14-day initial care, 35-day billing window (75 with a notice of
  initiation within 21 days of first treatment), carrier pays in 30 days (90 if
  investigating), demand letter only once overdue. A blank accident state
  counts as FL. Per patient: EMC status -> $10,000 / $2,500 limit, used = what
  the carrier paid us + "paid to others" (typed from the carrier's PIP log - the
  limit is shared by every provider), left, and open bills at 80%.
  Denials are typed in from the mailed EOB (type -> suggested next step); the
  **demand letter** (627.736(10)) prints only once the claim is overdue, needs
  claim #, carrier, provider and the carrier's OIR demand address, and after
  mailing the carrier gets 30 days from the green-card date. Everything is paper
  and mail - nothing is sent electronically. `test_fl_pip.py` = 35 checks.
  **Procedure Code Library** (`px-` records, Codes tab): one entry per code +
  modifier; typing a code on a claim fills description/charge (a $0 never
  overwrites) and blank units/modifier/pointer. "From Past Claims" seeds it
  from codes actually billed - nothing invented, charges need checking.
  **Company files, as in EZClaim** (one per office/LLC): each is a separate
  vault - patients, claims, payments, libraries, settings, account numbers.
  The first company, `Main`, is the original vault (nothing moved); new ones
  live in `thunder-claims/vault-companies/<Name>/` (gitignored), registry in
  `~/.thunder/claims_companies.json`. Switch via the orange Thunder Claims
  button; the title and status bar name the open company. Owner creates
  companies; per-user access with `claims_web.py grant|revoke <user>
  <Company|*>` (`companies` lists them). Users with no list = all. **Backups are
  per company**: `THUNDER_VAULT=<company dir> vault.py backup`.
- `/status`'s `gpu` block now reads the **real** GPU — nvidia-smi plus Ollama's
  `/api/ps` (`gpu_state()` in `app.py`). It used to ask thunder-genai on :9010,
  so once that was disabled `gpu.up` was stuck false and the phone showed the
  card as down while it was answering every message. `/system`'s `generators`
  key still means thunder-genai and is still correctly false.
- **Port 11434 is firewalled as of 2026-09-29** — `net-lockdown/port-11434.sh`
  has been **run**. Ollama still has no auth of any kind; the packet filter is
  the only thing protecting it. Allowlist is localhost + **.15 odris** +
  **.11 cache**, everything else DROPped, v4 and v6, in a dedicated
  `THUNDER-OLLAMA-IN` chain so it cannot disturb the uid 994/997 egress rules.
  Persisted to `/etc/iptables/rules.v4`/`.v6`. Undo:
  `sudo bash net-lockdown/unlock-11434.sh`.
  **Cache is not optional** and is in the allowlist deliberately:
  `thunder-cache.service` is active and enabled, has no GPU, and sends every
  batch job to Main's Ollama — blocking .11 would break the overnight worker
  silently. Verified from all four boxes. Note the other nodes have **no
  `curl`** — test reachability with `ssh <node> python3 -c '...urllib...'`.
- Chat model: **`thunder-gptoss:latest`** — gpt-oss 20B MXFP4 (OpenAI).
  `THUNDER_MODEL` env var. Unlike the old `thunder:latest`, it bakes in **no
  system prompt** — it is gpt-oss with `num_ctx 16384` and `temperature 0.6`,
  and the persona comes from `SYSTEM_PROMPT` in `app.py` at request time.
- Medical, claims extraction and the nightly memory consolidation **all run on
  `thunder-gptoss:latest` too**, as of 2026-09-29. `THUNDER_MEDICAL_MODEL`,
  `CLAIMS_MODEL`, `CONSOLIDATE_MODEL`. One model, already resident, so a
  medical question or the 3am job no longer evicts the chat model.
  The official **`mistral-small:24b`** is kept installed as a one-env-var
  fallback for claims — it reads provider NPIs slightly more reliably. See
  `reports/model-origin-audit-2026-09-29.md` for the measured comparison.
- Video and photo: **switched off and deleted (2026-09-29).** `thunder-genai` is
  stopped and disabled, and the Wan / StepFun / HiDream weights were **deleted
  from Main** the same day — `/home/genai/genai/models/` is now empty and
  `/mnt/thunder-data2/genai-models` is gone. There is no local copy of those
  anywhere on the fleet. FLUX.1-schnell and FLUX.1-Kontext were **also deleted
  from Main** and now exist **only** on serverus at
  `/mnt/bulk/thunder-backups/genai-archive/` (weights + the genai code and unit
  files, no venv), so the image side can be rebuilt if it is ever wanted — that
  copy is **sha256-verified on both sides**, all 159 model files. It is the only
  copy: do not delete it.
  `/video`, `/creations` and the Studio tab have no backend now.
- Voice: **removed from the app 2026-09-29 (Blayne: "wasn't a good idea, wastes more
  than it is useful").** Do not re-add spoken replies or the voice picker. The
  mic button (dictation *to* Thunder) stays. Server side still has: Kokoro is wired in and is what `/voices` now serves — 64 voices,
  24kHz, Apache-2.0, on Main. Piper on Odris remains the fallback. The old note
  here said Kokoro was "proven but not yet wired in"; that is out of date.
  Narrating 23 deck slides took 47s end to end.

## Hard-won facts — do not relearn these

- **No Chinese-origin or anonymously-modified weights in any live role
  (2026-09-29 audit + cleanup). Origin is judged by architecture/base blob, not
  by tag.** `thunder:latest` looked French and was: Mistral Small 24B — but
  abliterated and republished by the anonymous `huihui_ai` account, and the tag
  said none of that. Chat, medical, claims and the nightly job now all run on
  gpt-oss (OpenAI). `thunder-claims/extract.py` enforces this in code by asking
  Ollama what the model *is*; it fails closed on anything it cannot identify.
  **True on disk too, as of 2026-09-29**: the shelved Wan/StepFun/HiDream
  diffusion weights were deleted from Main that day, verified by a fleet-wide
  `find` across `/` and all three data drives — the only hits left are the
  `diffusers` *library* source in the genai venv and some download logs, no
  weights. Every model `ollama list` reports was re-checked against
  `BLOCKED_ARCH`: no matches.
- **Flash attention is already on — don't "enable" it again.** Ollama 0.33.3
  starts every runner with `--flash-attn auto`, and the journal says
  `resolve_fused_ops: Flash Attention enabled` on every load.
  `OLLAMA_FLASH_ATTENTION=1` forces what auto already picked and buys nothing.
  It was set (harmlessly) by the tuning drop-in until that was removed on
  2026-09-29; nothing sets it now, and the journal still says Flash Attention
  is enabled. That is the point: auto already gets it right.
- **`q8_0` KV was tried on 2026-09-29 and REMOVED the same day — it made chat
  5.6% slower. Don't install it again without a reason.** It was genuinely in
  effect while it was on, not a silent fallback: the runner showed
  `--cache-type-k q8_0 --cache-type-v q8_0` and the cache allocated at q8_0.
  gpt-oss's KV cache is tiny to begin with (sliding-window attention, 12 KV
  layers at head dim 64), so halving it **414 MiB → 220 MiB** saved only
  **192 MiB of 24576 — 0.8% of the card** — while costing **201.4 → 190.1 tok/s**.
  The run sets didn't overlap, so it was real, not noise: dequantising on every
  attention read isn't paid for when there was no bandwidth pressure to relieve.
  **Bad trade at today's 11GB-of-24GB usage; only worth revisiting if context
  grows well past 16384.** Blayne made the call to revert; the drop-in is kept
  at `thunder-main-api/ollama-tuning.conf` for reference but is **not** deployed
  to `/etc/systemd/system/ollama.service.d/`, which now holds only
  `override.conf` (`OLLAMA_HOST`, `OLLAMA_KEEP_ALIVE`). Re-measured after the
  revert: **201.5 tok/s, KV back at f16 414 MiB** — full speed restored.
  Ignore `KV cache shifting is not supported` in the log — it predates all of
  this and is a property of gpt-oss's iSWA.
- **Thunder cannot see its own runtime config.** Asked its context window it
  guessed "30-k range" when it is 16384 (it did flag the uncertainty). `num_ctx`,
  the model name and the GPU state are facts about the running process that
  nothing puts in front of the model — fix via the memory profile or a
  fleet-status tool, not by hardcoding a number in the prompt.
- **Measured chat speed is ~201 tok/s as currently configured** — 201.5 tok/s
  re-measured after the q8_0 revert, against 201.4 before it went on and 190.1
  while it was on (gpt-oss 20B, 16384 ctx, 400-token reply, 2026-09-29). That is
  not inconsistent with the 55.5 tok/s above: that was the *dense* 24B. gpt-oss
  is MoE with ~3.6B active per token.
- **Ollama reloads the model if `num_ctx` changes between requests** — it keys
  the runner on model *and* context size, so a mismatched call evicts 12GB and
  reloads it (~10s of dead air). Every chat-model call must send the same
  `THUNDER_NUM_CTX`; `forge.py`, `consolidate.py`, `extract.py` and
  `warm_model` were all missing it. Embedding calls must **not** have it —
  nomic-embed-text has its own 2048 runner.
- **The 3090 is compute capability 8.6, so fp8 does not work at all.**
  `torch._scaled_mm` needs 8.9+. NF4 (bitsandbytes) works; fp8 hard-fails.
- **The monitor costs 94MB of VRAM, so moving the cable is not worth it.**
  gnome-shell 82 + Xwayland 6 + snapd 6. There is also **no iGPU to move it
  to**: `lspci` shows only the 3090 and no `i915` loads — the Q87 board has the
  i7-4790's HD 4600 disabled in BIOS. TTS on the card costs 1328MB, fourteen
  times more.
- **Sequential CPU offload cannot be used with bitsandbytes 4-bit weights** —
  "Cannot copy out of meta tensor". `apply_offload` falls back automatically.
- **`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` is required** for
  720p/1080p. It reclaims ~4GB of fragmentation and is the whole difference
  between OOM and working.
- **Wan's VAE must be float32.** In bf16 it outputs noise.
- **Frame count IS motion duration.** TI2V-5B is 24fps, A14B is 16fps.
  Exporting at the wrong rate plays the clip at the wrong speed.
- **Video cannot be split across GPUs.** Diffusion does not shard. More cards
  help chat, never video.
- **Main is a Haswell i7-4790 on a Lenovo Q87 SHARKBAY board (ThinkCentre
  M93p)** — not Ivy Bridge, which an earlier note got wrong. Four DIMM slots,
  all full of 8GB DDR3, `Maximum Capacity: 32 GB`. That ceiling is real and
  there is no upgrade path on this board.
- **RAM cannot be borrowed from another machine, but it can be borrowed from
  the SSDs.** Swap on Main is 32GB on each of the three data drives, all at
  `pri=10`, so the kernel stripes across them: measured **1.55 GB/s**, against
  0.125 GB/s for gigabit ethernet. Overflow memory from Main's own disks is
  twelve times faster than anything another tower could offer over the wire,
  which is why pooling memory across the fleet is not worth attempting.
  `vm.page-cluster=0` (`/etc/sysctl.d/60-thunder-swap.conf`) because the
  default of 8 pages per fault is a spinning-disk optimisation.
  `model_fits_in_ram()` counts this swap, but only up to 35% of a model's
  weights — past roughly a third the kernel thrashes instead of streaming and
  the timing stops being predictable.
- **The other towers cannot be beefed up.** thunder-cache/engine are Ivy
  Bridge, and the six spare M81p are Sandy Bridge LGA1155 — four slots, 32GB
  max, same wall. Six of them is six separate 32GB ceilings, not 192GB.
- **Distributing a model across the fleet works, and costs 30x.** llama.cpp's
  RPC backend does pool memory across machines (unlike diffusion, which cannot
  shard at all), so this was worth testing properly. Measured on the 24B, same
  model, same prompt:

  | backend | tok/s |
  |---|---|
  | 3090 alone | **55.5** |
  | 3090 + serverus | 2.97 |
  | 3090 + serverus + engine + cache | **1.80** |

  **Adding the two weak nodes made it 40% slower than one node.** Every token
  walks the whole pipeline, so each extra hop adds latency and lands more
  layers on older silicon — the fleet runs at the speed of its slowest member
  and gets worse as it grows. This is the measured answer to "would more old
  towers help": no, they would actively hurt.

  It is still the only way to run a model too big for any one box, and 1.8
  tok/s is ~50k tokens over an eight-hour night, which suits the overnight
  batch worker. It is not a path to a fast large model.

  The real conclusion is the reframe: **one machine with a lot of RAM beats
  five machines with distributed RAM by more than an order of magnitude**,
  because local DDR3 is ~12 GB/s and gigabit is 0.125 GB/s.

  Binaries are at `~/llamacpp` on Main and the three idle nodes (release
  b11140, which ships per-microarch CPU backends including ivybridge and
  sandybridge). `ggml-rpc-server` has **no authentication at all** — upstream
  says trusted networks only. It was left shut down after the test; do not
  leave it listening on 0.0.0.0.
- **Python is 3.14 everywhere**, so many ML wheels don't exist (spacy fails,
  misaki fails). onnxruntime works.
- **`genai` and `ollama` (UIDs 994/997) are under iptables egress lockdown** —
  LAN + loopback only. To install for `genai`, download wheels as `blayne` and
  `pip install --no-index --find-links`. Its venv's `pip` script has a stale
  shebang; use `python -m pip`.
- Blayne's account can edit `genai`'s files via `sg genai -c "..."` but cannot
  restart the service without sudo.
- **GitHub's unauthenticated API is 60 req/hour for the whole house.** Polling
  it from Main can silently stop the phone seeing app updates.

## Android app

Local builds work: `ANDROID_HOME=/home/blayne/android-sdk`,
`JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64` (Gradle 8.9 rejects Java 25),
`./gradlew assembleDebug`. **Always compile locally before pushing** — CI logs
need auth and two releases were lost to a missing import and an unescaped
apostrophe in a string resource.

Signing uses a fixed key from the `ANDROID_DEBUG_KEYSTORE_B64` secret, so
builds install over each other. Verify a published APK with
`scratchpad/verify_apk.py` — these are v2-signed, so `keytool -printcert`
silently prints nothing.

CI publishes a GitHub Release with the asset named `thunder.apk`, giving a
stable URL. `/app/version` resolves the latest release server-side.

## API contract (Android depends on these)

Existing keys never change; new ones are additive.

    GET  /status          + "gpu": {up, loaded, loading, busy, progress{step,total}}
    POST /chat            {message, voice} -> {reply}
    POST /chat/stream     ndjson {"delta"} then {"done":true}
    GET  /greeting        instant, never loads a model
    POST /warm            preloads the chat model
    GET  /voices          proxied from Odris
    POST /speak           {text, voice} -> wav
    GET  /system          full health + bottlenecks
    GET  /app/version     update info
    POST /video           {prompt, style, duration, quality}
    GET  /creations/{id}  url = real first frame once done

Quality tiers: `480p|720p|1080p` and portrait `480p_v|720p_v|1080p_v`.
Duration caps (VRAM, enforced server-side): 480p 25s, 720p 12s, 1080p 6s.

## Measured timings (3090, A14B, 4 steps, 16fps)

5s@480p ~4min · 5s@720p ~8min · 5s@1080p ~22min. Scales with length.

## Priorities (set by Blayne 2026-09-27) — read this first

**Best model and real tools come before everything else.** Months were spent
building on top of `thunder:latest` without ever asking whether it was still the
best model for the card. That must not happen again: at the start of any
substantial work, ask whether the model or the tool layer is the real bottleneck.

1. **Model**: the smartest, fastest, best-at-coding model that fits the 3090,
   chosen by a measured shootout (coding tests that are executed, fabrication
   traps, speed, VRAM) — never by reputation. The abliterated base may be part
   of why Thunder fabricates; measure it.
2. **Real tool calling.** As of this date Thunder has none: web search is
   keyword-triggered and pasted into the prompt (`maybe_augment_with_search` in
   `thunder-main-api/app.py`); the model never decides to use a tool. Build real
   tool calling: search, page reading, sandboxed code execution, files, claims
   pipeline, memory, fleet status.
3. **Odris is the gatekeeper for every tool call.** Allowlist, input checks,
   logging, refusal. It is the only box with internet; Main and claims data stay
   off it.
4. **Honesty enforced in code, not the prompt**: if it didn't look it up and
   doesn't know, it says so.

**Video and image generation are shelved.** They work; don't spend effort there.
The whole 3090 goes to chat. Weights/config are to be archived on serverus
(copy first, verify, delete from Main only when Blayne says).

Dad and one more user come later, not now.

## Where this is going

The video work exists and functions, but **the real opportunity is the family
business**: they hand-bill medical/injury claims and pay for Google storage.
`Thunder-chat-v3/thunder-claims/` prototypes scan → OCR → extracted fields →
mechanical validation, and it works — it caught the model corrupting an ICD-10
code and dropping the billing provider.

The moat is genuine: patient data cannot go into cloud AI without a BAA, and
Thunder is local by construction.

**Synthetic patients only. No real PHI has touched any of this.**

The **technical** safeguards are now done, and each was verified rather than
assumed (see the commit messages for what was actually tested):

- **Auth**: bearer tokens, `THUNDER_AUTH=required`, audit log. Default off
  until Blayne has pasted a token into the app.
- **TLS**: https on **8443**, fleet's own CA. Plaintext 8080 still runs during
  migration — `thunder-main-api/tls/README.md` has the order to switch it off.
  The CA cert is bundled in the app at `res/raw/thunder_ca.crt`;
  **`thunder-data/tls/ca.key` must never leave Main.**
- **Encryption at rest + encrypted backups**: `thunder-claims/vault.py`.
  AES-256-GCM envelope encryption, per-record keys, blind indexes for search
  without decrypting, audit on every access, key rotation, passphrase-encrypted
  backups. `test_vault.py` is 34 checks, mostly attacks (tamper, ciphertext
  relocation, wrong key, weak passphrase, modified archive). All passing.
- **Honeyfiles**: `thunder-main-api/canary/`. Flips `/status` to
  `security_alert`, which the app already shows.

What remains is **not code**: risk analysis, written policies, workforce
training, BAAs. Say that plainly — good crypto is not compliance, and the gap
is paperwork. Do not imply otherwise to him.

Two things to never overstate: encryption at rest does nothing against root on
a running box, and a blind index leaks equality. Both are documented in
`thunder-claims/README.md`.

Also wanted: Thunder as an overnight batch worker (his original Cache plan) —
queue work, draft and flag, submit nothing, report in the morning.

## Memory

Most of the distance between Thunder and a frontier model is context, not
reasoning. `thunder-main-api/memory.py` holds three things:

- **profile** (`/memory/profile`) - always injected: who Blayne is, how he
  types (with his shorthand), the fleet, the hardware facts that are easy to
  get wrong. **The single most effective knob on answer quality.**
- **facts** - recalled by meaning via nomic-embed-text, only when relevant.
- **documents** - the handbook and the TLS/claims/honeyfile/code-vault docs,
  chunked on headings. Re-ingest with `POST /memory/ingest` after editing them
  or Thunder will answer from a stale copy.

Two things learned the hard way, both in the commit history:

1. **Retrieval working is not retrieval being used.** Notes recalled at 0.749
   were ignored in favour of the training prior until they were moved to
   immediately before the user's question and labelled as authoritative.
2. **Never let it read its own replies back.** The overnight job originally
   learned Thunder's own hallucinated file path as a fact about Blayne.

`consolidate.py` runs nightly at 3am (`thunder-consolidate.timer`) and reads
only **Blayne's** messages, never Thunder's. It **proposes**; nothing enters
memory unreviewed - see `/memory/pending`, then approve or reject. Contradictory
proposals are flagged against each other rather than one being picked.

Do not "improve" this by writing straight to memory. An unsupervised model
writing its own beliefs into its own long-term memory compounds: one confident
mistake becomes permanent context for every later answer, and afterwards there
is no way to tell which facts were real.

## How Blayne works

- Baby steps, one thing at a time. He is often on a phone.
- **Build it, don't describe it.** He lost hours to explanations of things that
  had not been built yet (the voice grid and version display were discussed
  long before they existed).
- **Verify before claiming.** Check the APK, check the endpoint, check the log.
  Saying "found the bug" before confirming it cost real trust in this session.
- Chat quality should feel like Grok: direct, useful, not a chatbot toy.
- A frontier-model comparison will disappoint him if oversold. Say where a 24B
  is genuinely weaker.
