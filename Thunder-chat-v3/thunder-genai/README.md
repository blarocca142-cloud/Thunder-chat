# Thunder GenAI service

Image, video, and photo-edit generation. Runs on Main (the only GPU box), in
its own process so a long generation never blocks chat.

## Why it lives in two places

The service runs as the `genai` user from `/home/genai/genai/`, which is
outside this repo. That separation is deliberate: `genai` is one of the
accounts under UID-based iptables lockdown (LAN + loopback only, no internet),
so it cannot sit in Blayne's home directory.

**This repo is the source of truth.** Edit here, then deploy:

```
sudo -u genai cp Thunder-chat-v3/thunder-genai/genai_server.py /home/genai/genai/genai_server.py
sudo systemctl restart thunder-genai
```

Models are NOT in the repo (hundreds of GB). They live at
`/home/genai/genai/models/` and `/mnt/thunder-data2/genai-models/`.

## Configuration (systemd drop-ins in /etc/systemd/system/thunder-genai.service.d/)

| Variable | Values | Notes |
|---|---|---|
| `GENAI_VIDEO_MODEL` | `5b`, `a14b`, `a14b_nf4` | `a14b` is fp8 and needs compute capability 8.9+, so it will NOT run on the 3090 |
| `GENAI_OFFLOAD_VIDEO` | `none`, `model`, `sequential` | |
| `GENAI_OFFLOAD_IMAGE` | as above | FLUX is 12B+; `sequential` keeps RAM usage survivable on 30GB |
| `GENAI_OFFLOAD_EDIT` | as above | |
| `GENAI_IDLE_UNLOAD` | seconds | unload pipelines after idle so Ollama can have the card back |
| `PYTORCH_CUDA_ALLOC_CONF` | `expandable_segments:True` | **required for 720p/1080p** - reclaims ~4GB of fragmentation |

## Hardware notes that cost real time to learn

- Wan's VAE must be **float32**. In bf16 it outputs noise.
- The 3090 is compute capability 8.6. `torch._scaled_mm` needs 8.9+, so **fp8
  models hard-fail**. NF4 (bitsandbytes) works; fp8 does not.
- The A14B NF4 build ships without step distillation, so the LightX2V LoRAs
  are applied at load to get back to a 4-step budget.
- VAE decode - not model weights - is the memory ceiling at high resolution.
  Tile size scales with requested height for that reason.
- One workload owns the GPU at a time. Loading a pipeline evicts the others,
  and the chat model is evicted here rather than trusting callers to do it.

## Frame rate is not a free choice

The frame count IS the motion duration. Each model has a native rate from its
own model card - TI2V-5B is 24fps, the A14B line is 16fps - and exporting at
anything else plays the clip at the wrong speed. This was 8fps for both
models, so every video ran at half (A14B) or a third (5B) of its intended
speed with a fraction of the frames it needed.

## Measured timings (RTX 3090, A14B NF4, 4 steps, 16fps)

Correct-speed video costs about 2x what the old half-speed output did, because
it needs twice the frames.

| Job | Time |
|---|---|
| 5s @ 480p | ~4 min |
| 5s @ 720p | ~8 min |
| 5s @ 1080p | ~22 min |
