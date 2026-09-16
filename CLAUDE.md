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
| thunder-cache | .11 | idle | i5-3470, 22GB |
| thunder-engine | .12 | safety yes/no (9002) | i7-3770, 30GB |
| serverus | .13 | memory (9001) | **Xeon E3-1230 v5** — best CPU in the fleet, barely used |
| odris | .15 | heartbeat 9003, websearch 9004, admin 9005, **TTS 9006** | Radeon 550 **4GB**, 30GB RAM |

SSH works to all of them from Main via the aliases in `~/.ssh/config`
(`odris`, `serverus`, `thunder-cache`, `thunder-engine`). **Use the aliases** —
raw IPs default to the wrong username and look like an auth failure.

Odris services are system units needing root Blayne doesn't have the password
for. Deploy by copying the file and `pkill`ing the process — `Restart=always`
brings it back on the new code in 3s. The TTS service is a **systemd user**
unit with lingering enabled, so `systemctl --user restart thunder-tts` works.

## What runs where

- **Main**: `thunder-main` (FastAPI :8080), `thunder-genai` (:9010, runs as
  `genai`), `ollama` (:11434)
- Chat model: **`thunder:latest`** — 23.6B, Q4_K_M, abliterated Mistral base,
  custom system prompt. `THUNDER_MODEL` env var.
- Video: **Wan 2.2 T2V-A14B NF4 + LightX2V LoRAs**, 4 steps.
  `GENAI_VIDEO_MODEL=5b|a14b|a14b_nf4`
- Photo: FLUX.1-schnell. Edit: FLUX.1 Kontext.
- Voice: **Piper** on Odris, 9 voices, ~800ms/sentence. **Kokoro** (better,
  Apache-2.0, 92MB ONNX) is proven working on Main but not yet wired in.

## Hard-won facts — do not relearn these

- **The 3090 is compute capability 8.6, so fp8 does not work at all.**
  `torch._scaled_mm` needs 8.9+. NF4 (bitsandbytes) works; fp8 hard-fails.
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

## Where this is going

The video work exists and functions, but **the real opportunity is the family
business**: they hand-bill medical/injury claims and pay for Google storage.
`Thunder-chat-v3/thunder-claims/` prototypes scan → OCR → extracted fields →
mechanical validation, and it works — it caught the model corrupting an ICD-10
code and dropping the billing provider.

The moat is genuine: patient data cannot go into cloud AI without a BAA, and
Thunder is local by construction.

**Synthetic patients only. No real PHI has touched any of this.**

**The blocker is not hardware — it is that Thunder's API has no authentication
at all and runs cleartext HTTP.** Fix that and TLS first. Then encryption at
rest, audit logging, encrypted backups with a tested restore. Those are
technical safeguards only; risk analysis, policies, training and BAAs are
organisational work needing a professional, and that should be said plainly
rather than implied away.

Also wanted: Thunder as an overnight batch worker (his original Cache plan) —
queue work, draft and flag, submit nothing, report in the morning.

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
