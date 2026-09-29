# Model origin audit — 2026-09-29

Read-only audit. Nothing was deleted, pulled, retagged or restarted.

Prompted by Blayne: "thunder ai currently has china stuff in it I thought."
Short answer: **not in the paths Thunder uses for chat, medical or claims.
There is Chinese-origin AI on the box — one leftover Qwen from the shootout,
and the shelved video/image stack, which is Alibaba's Wan plus two other
Chinese labs.** Details below.

## How origin was determined

Two different kinds of evidence, kept separate on purpose:

- **Verified locally**: the architecture string Ollama reports, the blob
  SHA-256 behind each tag, the manifest each blob was pulled from, and the
  live environment of the running `thunder-main` process
  (`/proc/<pid>/environ`, not just the unit file). These are facts from this
  machine.
- **Not verifiable locally**: which lab/country actually produced a base
  model. That comes from knowing the labs. It is reliable for the well-known
  ones (gpt-oss → OpenAI, gemma3 → Google, qwen3moe → Alibaba) but it is not
  something a file on Main proves.

Origin is judged by **architecture and base blob, not by tag name**, because
`thunder:latest` is a local tag that can be rebuilt FROM anything. That is the
same rule `thunder-claims/extract.py` already enforces in code.

## What each Thunder role actually uses

Verified from the live process environment, not the unit file — the unit file's
base section still says `THUNDER_MODEL=dolphin3`, overridden by the drop-in
`/etc/systemd/system/thunder-main.service.d/model.conf`.

| Role | Model | Set by | Architecture | Maker | Country |
|---|---|---|---|---|---|
| Chat | `thunder-gptoss:latest` | `THUNDER_MODEL` (drop-in) | gpt-oss 20.9B MXFP4 | OpenAI | **US** |
| Medical | `thunder-gptoss:latest` | `THUNDER_MEDICAL_MODEL` (drop-in) | gpt-oss 20.9B MXFP4 | OpenAI | **US** |
| Vision / picture reading | `thunder-vision:latest` | `THUNDER_VISION` default in `app.py:85` | gemma3 3.9B + CLIP projector | Google | **US** |
| Embeddings (memory recall) | `nomic-embed-text:latest` | `EMBED_MODEL` in `memory.py:49` | nomic-bert 137M | Nomic AI | **US** |
| Embedding host | serverus `10.168.168.13:11434` | `THUNDER_EMBED_HOST` default, `memory.py:45` | — | — | — |
| Claims extraction | `thunder:latest` | `CLAIMS_MODEL` default, `extract.py:10` | llama 23.6B (Mistral Small) | Mistral AI (abliterated by a third party) | **France** base — see note |
| Nightly memory consolidation | `thunder:latest` | hard-coded, `consolidate.py:38` | llama 23.6B (Mistral Small) | Mistral AI (abliterated by a third party) | **France** base — see note |
| OCR (claims scans) | tesseract 5.5.0 | `intake.py`, `evaluate.py` | not a neural LLM | Google-originated, now community | US/Germany |
| TTS (serving `/voices`) | Kokoro-82M ONNX | `kokoro_server.py`, `/home/blayne/tts/kokoro` | StyleTTS2-family, Apache-2.0 | hexgrad | **US** |
| TTS fallback | Piper, 13 en_US/en_GB voices | Odris `/home/blayne-odris/tts/voices` | VITS ONNX | Rhasspy | **US** |

**No Chinese-origin model is in any of these roles.**

serverus runs Ollama from `/home/admin-b/ollama/bin/ollama` and holds exactly
one model, `nomic-embed-text:latest`. Odris has no Ollama at all — it runs TTS,
search, and the tool gate only.

### The `thunder:latest` nuance — worth knowing, not alarming

`thunder:latest`, `thunder-bare:latest` and `huihui_ai/mistral-small-abliterated:24b`
are all the **same weights**: model blob `sha256-8ad25d75a88d` in all three
manifests. So `thunder:latest` is Mistral Small 24B (Mistral AI, France) that
was abliterated — had its refusal behaviour stripped — and republished by the
third-party `huihui_ai` account on the Ollama registry.

The base model is French. The **modifier is a third party whose identity is not
verifiable from anything on this machine**; the account name and its model
cards are Chinese-language. That is a supply-chain question about who touched
the weights, not a question of which lab trained them. It is a different and
milder concern than running a Qwen, but it is not nothing: these are
fine-tuned weights from an anonymous uploader, and they are currently the
default for claims extraction and for the nightly job that proposes memory.

CLAUDE.md already notes the chat base is "abliterated Mistral"; this audit adds
that the abliteration came from `huihui_ai` specifically.

`thunder:latest` was resident on the GPU at the time of this audit — loaded at
**03:04 EDT on 2026-09-29** by the nightly consolidate timer, which is the
expected 3am run, not unexplained activity.

## Every model on Main

| Model | Role | Architecture | Maker | Country |
|---|---|---|---|---|
| `thunder-gptoss:latest` | **chat + medical (active)** | gpt-oss 20.9B | OpenAI | US |
| `shootout-gptoss20b:latest` | unused (same blob as above) | gpt-oss 20.9B | OpenAI | US |
| `thunder-vision:latest` | **vision (active)** | gemma3 3.9B + CLIP | Google | US |
| `nomic-embed-text:latest` | **embeddings (active)** | nomic-bert 137M | Nomic AI | US |
| `thunder:latest` | **claims + consolidation (active)** | llama 23.6B | Mistral AI, abliterated by `huihui_ai` | France base |
| `thunder-bare:latest` | unused (same blob as `thunder:latest`) | llama 23.6B | Mistral AI, abliterated by `huihui_ai` | France base |
| `huihui_ai/mistral-small-abliterated:24b` | unused (source of the above) | llama 23.6B | Mistral AI, abliterated by `huihui_ai` | France base |
| `mistral-small:24b` | unused | llama 23.6B | Mistral AI (official) | France |
| `shootout-mistral-small-3.2:latest` | unused (shootout) | llama 23.6B | Mistral AI | France |
| `shootout-mistral-small-3.2fix:latest` | unused (shootout) | llama 23.6B | Mistral AI | France |
| `shootout-ms32-tc:latest` | unused (shootout) | llama 23.6B | Mistral AI | France |
| `devstral:latest` | unused | llama 23.6B | Mistral AI | France |
| `thunder-code:latest` | unused (same blob as `devstral`) | llama 23.6B | Mistral AI | France |
| `shootout-gemma3-27b:latest` | unused (shootout) | gemma3 27B | Google | US |
| `dolphin3:latest` | unused (stale unit-file default, overridden) | llama 8B | Cognitive Computations, on Meta Llama 3.1 | US |
| **`shootout-qwen3-coder-30b:latest`** | **unused — shootout leftover** | **qwen3moe 30.5B** | **Alibaba / Tongyi** | **CHINA** |

**One Chinese-origin LLM is present: `shootout-qwen3-coder-30b:latest`.** It is
a leftover from the coding shootout of 2026-09-28, it is wired to nothing, and
it was not loaded at any point during this audit. It is 18 GB of disk.

## Model weights outside Ollama

`~/llamacpp` holds **no GGUFs** — the RPC test binaries only.
genai has no separate model tree; it loads from the HuggingFace cache, plus
FLUX Kontext from `/home/genai/genai/models/flux1-kontext-dev`.

`~/.cache/huggingface/hub` — the shelved video/image stack:

| Repo | Role | Maker | Country |
|---|---|---|---|
| **`lopho/Wan2.2-T2V-A14B-Diffusers_nf4`** | **active video model** (`GENAI_VIDEO_MODEL=a14b_nf4`) | community NF4 requant of **Alibaba Wan 2.2** | **CHINA** (base) |
| **`Wan-AI/Wan2.2-TI2V-5B`** | selectable (`5b`) | **Alibaba / Tongyi Wan** | **CHINA** |
| **`Wan-AI/Wan2.2-TI2V-5B-Diffusers`** | selectable (`5b`) | **Alibaba / Tongyi Wan** | **CHINA** |
| **`inference-sh/Wan2.2-TI2V-5B-LightX2V-Diffusers`** | LightX2V step-distilled | **Alibaba base + LightX2V** | **CHINA** |
| **`yetter-ai/Wan2.2-T2V-A14B-Lightning-FP8-Diffusers`** | unusable — fp8 needs CC 8.9+, the 3090 is 8.6 | **Alibaba base** | **CHINA** |
| **`stepfun-ai/Step1X-Edit`** | unused — Kontext is the wired editor | **StepFun** | **CHINA** |
| **`stepfun-ai/Step1X-Edit-v1p1-diffusers`** | unused | **StepFun** | **CHINA** |
| **`HiDream-ai/HiDream-I1-Full`** | unused | **HiDream.ai** | **CHINA** |
| **`HiDream-ai/HiDream-E1-1`** | unused | **HiDream.ai** | **CHINA** |
| `black-forest-labs/FLUX.1-schnell` | photo generation | Black Forest Labs | Germany |
| `black-forest-labs/FLUX.1-Kontext-dev` | image editing (wired, `genai_server.py:88`) | Black Forest Labs | Germany |

**This is where the "china stuff" actually is.** The entire video pipeline is
built on Alibaba's Wan 2.2, and there are two more Chinese labs' weights
(StepFun, HiDream) sitting unused. Per CLAUDE.md, video and image generation
are **shelved** — but `thunder-genai` is still running on :9010 with
`GENAI_VIDEO_MODEL=a14b_nf4`, so the Wan weights are reachable, not archived.

These are diffusion models. They generate pixels from a prompt; they never see
claims data and are on a service that has no path to it. The risk is different
in kind from an LLM reading patient records.

## Guards already in code

`thunder-claims/extract.py:16-39` — `BLOCKED_ARCH` refuses to run claims
extraction on any model whose Ollama-reported architecture starts with qwen,
deepseek, glm, chatglm, internlm, baichuan, yi, minicpm, kimi, moonshot, ernie,
hunyuan or step. It is genuinely called (`extract.py:63`, raising
`BlockedModel` before any page is read), and it checks architecture rather than
tag name, so retagging a Qwen as `thunder:latest` would not sneak past it. It
also fails closed: a model it cannot identify is refused.

`thunder-main-api/tools.py:437-448` — separate reply-level checks for CJK
script and for the model claiming to be some other lab. That catches a model
that leaks its training identity; it is not an origin control.

The claims path goes scan → **tesseract OCR** → text → guarded extraction. The
vision model is not in it.

## Recommendations — nothing has been done, this is a proposal

1. **Delete `shootout-qwen3-coder-30b:latest`.** It is the one Chinese LLM on
   the box, it is used by nothing, and it reclaims 18 GB. The shootout that
   justified it is finished and written up in
   `reports/shootout-2026-09-28.md`. Nothing breaks.
2. **Decide what happens to the Wan / StepFun / HiDream weights.** Video is
   shelved, so the cleanest move is the archive-to-serverus plan CLAUDE.md
   already describes — copy, verify, then delete from Main. If video is truly
   done, stopping `thunder-genai` removes the only live Chinese-origin AI on
   the fleet. This is the bulk of the disk and the bulk of the honest answer
   to the question.
3. **Move `CLAIMS_MODEL` and `consolidate.py` off `thunder:latest`.** Not for
   Chinese-origin reasons — the base is French — but because both currently
   default to anonymously-modified weights, and `reports/switch-gpt-oss-2026-09-28.md`
   already flags that `CLAIMS_MODEL` was deliberately left behind pending
   extraction validation. Finishing that validation and pointing both at
   `thunder-gptoss:latest` would put every data-touching role on a named lab's
   model.
4. **Extend the origin guard to `VISION_MODEL`.** Today `thunder-vision` is
   gemma3, so there is no live exposure. But a photo sent through chat goes
   straight to `ollama_vision` (`app.py:2088`) with no architecture check, and
   the obvious upgrade for a 4B vision model is Qwen2.5-VL. The guard should
   cover that door before someone walks through it. Small change, reuses
   `model_origin_ok`.
5. **Drop the stale `THUNDER_MODEL=dolphin3` from the base unit file.** It is
   overridden and harmless, but it makes the unit file lie about what runs.
