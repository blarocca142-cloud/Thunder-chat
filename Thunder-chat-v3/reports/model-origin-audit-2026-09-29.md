# Model origin audit — 2026-09-29

The audit itself was read-only. **Blayne then approved acting on it, and the
"Actions taken" section at the bottom records what was actually done** —
including the two things that are still outstanding. Read that section before
trusting the present tense anywhere above it.

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

---

# Actions taken — 2026-09-29

Approved by Blayne against the A/B/C options above. Times are EDT (the journal
is UTC; a 07:12 line is 03:12 local).

## A. The leftover Qwen — done

`ollama rm shootout-qwen3-coder-30b:latest`. Gone from `ollama list`; the
Ollama blob store went from 162.5 GB to 144.0 GB, so **18.6 GB freed**. It was
wired to nothing, so nothing broke. That was the only Chinese-origin *LLM* on
the fleet.

## B. Claims and consolidation moved off `thunder:latest` — done

### The measurement

20 synthetic forms from `thunder-claims/synthetic.py` (invented patients — no
real PHI exists anywhere in this work), same forms and same OCR for all three,
run sequentially so each model had the whole 3090. `evaluate.py`, repair step
on. The `BLOCKED_ARCH` guard ran unchanged and was separately confirmed to
still report each model's real architecture (`llama`, `gpt-oss`, `nomic-bert`)
rather than trusting the tag.

| | `thunder:latest` (old) | **`thunder-gptoss`** (new) | `mistral-small:24b` |
|---|---|---|---|
| maker | Mistral AI, abliterated by `huihui_ai` | **OpenAI** | Mistral AI (official) |
| forms completed | 20/20 | **19/20** | 20/20 |
| fully correct | **8/20 (40%)** | 7/19 (37%) | 6/20 (30%) |
| wrong, validator flagged | 7 | 7 | 8 |
| **wrong, nothing flagged** | **5 (25%)** | **5 (26%)** | **6 (30%)** |
| ICD-10 recall / precision | 97% / 97% | **98% / 98%** | 93% / 93% |
| CPT recall / precision | 100% / 100% | 100% / 100% | 100% / 100% |
| forms with a dropped provider NPI | 1 | **3** | 1 |
| model time per form | **8.0s** | 8.3s | 10.4s |
| hard failures | 0 | **1** (empty response) | 0 |

**Honest reading: on 20 forms these three are within noise of each other.** The
silent-error rate — the only number that decides whether this saves money — is
effectively identical at 25/26/30%. Nobody won on accuracy.

Two real differences did show up, and both count against the model that was
chosen:

- **gpt-oss dropped both provider NPIs on 3 forms of 19** (case012, case014,
  case019) against 1 of 20 for either Mistral. case012 is an OCR problem common
  to all three; the other two are gpt-oss alone. All were caught by the
  validator — none were silent — but this is the exact failure the claims
  prototype was built to catch, so it is worth stating plainly rather than
  averaging away.
- **One form in twenty came back as an empty string** and killed the
  extraction with a `JSONDecodeError`. This is not the page: the same page
  then succeeded three times out of three. It is intermittent.

### The choice

**`thunder-gptoss:latest`**, on the stated tiebreak. It is ahead on
fully-correct and ICD-10 recall, it is faster, and it is *already resident on
the GPU* — so claims work and the 3am job no longer evict the chat model to
swap in a second 14 GB of weights. Every data-touching role is now one named
lab's model.

The official **`mistral-small:24b` was kept installed** rather than deleted,
because it is the better NPI reader and the fallback is one env var:
`CLAIMS_MODEL=mistral-small:24b`.

`extract.py` gained **a single retry** on an empty/unparseable response. Without
it the switch would have made extraction strictly less reliable than what it
replaced; with it, the one measured hard failure is covered.

### Defaults changed

| where | was | now |
|---|---|---|
| `thunder-claims/extract.py` | `CLAIMS_MODEL` → `thunder:latest` | `thunder-gptoss:latest` |
| `thunder-main-api/consolidate.py` | hard-coded `thunder:latest` | env `CONSOLIDATE_MODEL` → `thunder-gptoss:latest` |
| `thunder-main-api/app.py` | `THUNDER_MEDICAL_MODEL` → `thunder:latest` | `thunder-gptoss:latest` |
| `thunder-main.service` (base) | `THUNDER_MODEL=dolphin3` | `thunder-gptoss:latest` (matches the drop-in; no behaviour change) |
| `tls/thunder-main-tls.service` | `THUNDER_MODEL=thunder:latest` | `thunder-gptoss:latest` |
| `thunder-tune/bench.py` | default `thunder:latest` | `thunder-gptoss:latest` |
| `memory.py` profile + live `profile.md` | "Chat model is thunder:latest" | gpt-oss; video/photo gone |
| `TOOLS.md` | both defaults | updated |
| `thunder-modelfile` | buildable | marked **RETIRED** — its `FROM` would re-pull the abliterated weights |

Remaining matches for `thunder:latest` / `huihui` in the tree are historical
comments explaining what changed, not live references.

Retiring `thunder-modelfile` left the fleet's one remaining model with no
recipe in the repo, so `thunder-gptoss-modelfile` was added. Worth knowing:
**`thunder-gptoss` bakes in no system prompt.** It is plain `gpt-oss:20b` with
`num_ctx 16384` and `temperature 0.6`; Thunder's persona is sent per-request
from `SYSTEM_PROMPT` in `app.py`. CLAUDE.md described the chat model as having
a "custom system prompt", which was true of the Mistral build and is not true
now — corrected.

### Verification

- `test_tools.py` **111 passed**, `test_forge.py` **14 passed**,
  `test_vault.py` **34 passed**, `test_repair.py` **32 passed**.
- `test_speed_users.py` **could not run** — `fastapi.testclient` needs
  `httpx2` and neither `httpx` nor `httpx2` is installed under Python 3.14.
  Confirmed pre-existing by reproducing it on stashed code. Not fixed: pulling
  an unfamiliar package onto the box that will hold claims data is the exact
  risk this audit is about.
- `thunder-main` restarted. `/status` → `state: ok`,
  `model: thunder-gptoss:latest`, no canary alert. `/chat` answers.
- `thunder-consolidate.service` triggered manually at **03:55 EDT** — exit 0,
  clean journal, proposed nothing (only 1 new exchange). To actually exercise
  gpt-oss on that job it was then re-run **dry, against a throwaway copy** of
  the memory tree: all 139 exchanges, 28 batches, 14 proposed, 1 rejected as
  hedged, no errors. Live memory and `pending.json` were not touched.
- `ollama rm thunder:latest thunder-bare:latest huihui_ai/mistral-small-abliterated:24b`
  — all three gone. They shared one blob, so **14.3 GB freed**. `/status` and
  `/chat` re-checked afterwards and still healthy.

## C. The diffusion stack — partly done

### Done

`thunder-genai` is **stopped and disabled**. It held no VRAM at the time. This
removes the only live Chinese-origin AI on the fleet: the Wan weights are no
longer reachable by anything. `/video`, `/creations` and the app's Studio tab
now have no backend.

FLUX (Black Forest Labs, Germany) was copied to serverus at
**`/mnt/bulk/thunder-backups/genai-archive/`** — `models/flux1-schnell` and
`models/flux1-kontext-dev` (115.6 GB), plus `code/` with the genai source and
its systemd unit and drop-ins (no venv, no weights). `/mnt/archive` needs root
on serverus and admin-b has no passwordless sudo there, so the admin-b-owned
backups mount was used instead; it has 3.4 TB free.

**The copy is verified.** `sha256sum` was run over all 159 files on both
machines and the two lists were diffed: `VERIFY OK - every file matches`. The
hashes were taken from the file contents on each side independently, not from
rsync's own accounting, so this is a real check that the archive is readable
and byte-identical — not just that rsync exited zero. FLUX can be deleted from
Main whenever Blayne wants; the archive stands on its own.

### Correction to the audit above

The "Model weights outside Ollama" table said these live in
`~/.cache/huggingface/hub`. **They do not.** That cache holds only empty `refs`
stubs totalling 204 KB. The real weights are plain directories in two places:

| path | size | origin |
|---|---|---|
| `/home/genai/genai/models/wan2.2-ti2v-5b` | 20.0 GB | Alibaba |
| `/home/genai/genai/models/wan2.2-ti2v-5b-diffusers` | 34.2 GB | Alibaba |
| `/home/genai/genai/models/wan2.2-ti2v-5b-lightx2v` | 558 B | Alibaba + LightX2V |
| `/home/genai/genai/models/step1x-edit` | 52.5 GB | StepFun |
| `/home/genai/genai/models/step1x-edit-diffusers` | 25.7 GB | StepFun |
| `/home/genai/genai/models/hidream-e1-1` | 7.7 GB | HiDream.ai |
| `/mnt/thunder-data2/genai-models/wan2.2-t2v-a14b-nf4` | 23.2 GB | Alibaba (NF4 requant) |
| `/mnt/thunder-data2/genai-models/wan2.2-t2v-a14b-lightning-fp8` | 45.0 GB | Alibaba |
| `/mnt/thunder-data2/genai-models/wan2.2-lightning-loras` | 1.2 GB | LightX2V |
| **total** | **209.5 GB** | |

`HiDream-ai/HiDream-I1-Full` was listed in the audit but **is not on disk** —
only the empty HF stub. Nothing to delete.

### NOT done — needs Blayne

**The 209.5 GB above is still on disk, and FLUX is still on Main.** The
deletion was refused by the sandbox as irreversible local destruction, and that
refusal was not worked around. The exposure is already closed — `thunder-genai`
is disabled, so nothing can load these — but the disk is not reclaimed.

To finish, from Main:

```sh
sudo rm -rf /home/genai/genai/models/{wan2.2-ti2v-5b,wan2.2-ti2v-5b-diffusers,\
wan2.2-ti2v-5b-lightx2v,step1x-edit,step1x-edit-diffusers,hidream-e1-1} \
            /mnt/thunder-data2/genai-models
rm -rf ~/.cache/huggingface/hub          # 204 KB of empty stubs
# FLUX too - the serverus copy is verified, so this is safe to run:
sudo rm -rf /home/genai/genai/models/flux1-schnell /home/genai/genai/models/flux1-kontext-dev
```

## Disk

| | freed |
|---|---|
| Qwen shootout model | 18.6 GB |
| `thunder` / `thunder-bare` / `huihui_ai` (one shared blob) | 14.3 GB |
| **freed so far** | **32.9 GB** |
| still to reclaim (Chinese diffusion weights) | 209.5 GB |
| still to reclaim (FLUX on Main — archive verified, safe to delete) | 115.6 GB |

## Where this leaves the origin question

Every role that touches data or text — chat, medical, claims extraction,
nightly consolidation, vision, embeddings — runs on a model from a **named US
lab** (OpenAI, Google, Nomic). No Qwen, no DeepSeek, nothing from an anonymous
uploader. The guard in `extract.py` is unchanged and still fails closed.

### Re-audit after the removals

Every model still installed, re-checked by architecture through `/api/show`
rather than by tag — twelve in total, and not one matches `BLOCKED_ARCH`:

| family | models | origin |
|---|---|---|
| `gpt-oss` | `thunder-gptoss`, `shootout-gptoss20b` | OpenAI, US |
| `llama` | `mistral-small:24b`, `devstral`, `thunder-code`, `dolphin3`, `shootout-ms32-tc`, `shootout-mistral-small-3.2`, `shootout-mistral-small-3.2fix` | Mistral (FR) and Meta-derived, US/EU |
| `gemma3` | `thunder-vision`, `shootout-gemma3-27b` | Google, US |
| `nomic-bert` | `nomic-embed-text` | Nomic AI, US |

Note that Mistral Small 3.x reports `llama` as its family — that is the
architecture it reuses, not its provenance. This is the one place where judging
by architecture alone under-reports, and it under-reports in the safe
direction: it never lets a blocked family through, it only mislabels a European
model as Meta-derived.

Two things not to overstate:

- **The Chinese diffusion weights are still on the disk.** Disabled is not
  deleted. Until the `rm` above is run, "no Chinese-origin weights on Main" is
  not a true statement.
- **Recommendation 4 from the audit was not acted on.** `VISION_MODEL` still
  has no origin check. `thunder-vision` is gemma3 today so there is no live
  exposure, but the door is open and the obvious upgrade for a small vision
  model is a Qwen2.5-VL.
