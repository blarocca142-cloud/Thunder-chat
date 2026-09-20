"""Thunder image/video generation service. Runs on Main (only GPU in the
fleet), separate process from the chat API so a slow generation never blocks
chat. Keeps FLUX loaded in memory across requests. Stdlib HTTP server to
match the rest of the fleet - no new framework dependency.
"""
import gc
import json
import numpy as np
import urllib.request
import os
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import io

import torch
from diffusers import AutoencoderKLWan, FluxKontextPipeline, FluxPipeline, WanPipeline
from diffusers.utils import export_to_video, load_image

PORT = 9010
MEDIA_DIR = Path("/home/genai/genai/media")
MEDIA_DIR.mkdir(exist_ok=True)
FLUX_DIR = "/home/genai/genai/models/flux1-schnell"
WAN_DIR = "/home/genai/genai/models/wan2.2-ti2v-5b-diffusers"
WAN_A14B_DIR = "/mnt/thunder-data2/genai-models/wan2.2-t2v-a14b-lightning-fp8"
WAN_A14B_NF4_DIR = "/mnt/thunder-data2/genai-models/wan2.2-t2v-a14b-nf4"
LORA_DIR = "/mnt/thunder-data2/genai-models/wan2.2-lightning-loras"

# Two video models with very different step budgets. The A14B is Lightning
# distilled - it is tuned for ~4 steps and no classifier-free guidance, so
# running it at the 5B's settings would be both slow and wrong.
VIDEO_MODELS = {
    "5b": {"dir": WAN_DIR, "steps": 20, "guidance": 5.0, "guidance_2": None, "fps": 24},
    # Lightning distilled: no classifier-free guidance on either expert.
    # fp8 build - needs compute capability 8.9+, so it will NOT run on the 3090.
    "a14b": {"dir": WAN_A14B_DIR, "steps": 4, "guidance": 1.0, "guidance_2": 1.0, "fps": 16},
    # NF4 build - runs on Ampere. Ships without the step distillation, so the
    # Lightning LoRAs are applied on load to get the 4-step budget back.
    "a14b_nf4": {
        "dir": WAN_A14B_NF4_DIR,
        "steps": 4,
        "guidance": 1.0,
        "guidance_2": 1.0,
        "fps": 16,
        "loras": [
            (f"{LORA_DIR}/wan2.2_t2v_A14b_high_noise_lora_rank64_lightx2v_4step_1217.safetensors", "high", False),
            (f"{LORA_DIR}/wan2.2_t2v_A14b_low_noise_lora_rank64_lightx2v_4step_1217.safetensors", "low", True),
        ],
    },
    # NOT USABLE ON A 30GB MACHINE. Stripping the distillation LoRAs from an
    # NF4 model makes diffusers dequantise to bf16 to remove the adapter, which
    # takes the weights from ~14GB to ~28GB of system RAM and gets the process
    # killed. Kept for a future box with more RAM; quality mode uses 5B instead.
    "a14b_hq": {
        "dir": WAN_A14B_NF4_DIR,
        "steps": 24,
        "guidance": 3.5,
        "guidance_2": 3.5,
        "fps": 16,
    },
}

# One pipeline, both modes. The first attempt loaded a separate "video_hq"
# pipeline and the machine went into swap and was killed: with model offload
# the weights sit in system RAM, and two copies of a 14GB model does not fit
# in 30GB. The LoRAs are adapters - they can be switched off on the pipeline
# that is already loaded, which costs nothing and reloads nothing.


def video_cfg_for(mode: str) -> dict:
    if mode == "quality":
        return VIDEO_MODELS["5b"]
    return video_model_cfg()


def uses_safetensors(model_dir: str) -> bool:
    """Some community builds ship sharded .bin instead of safetensors; diffusers
    looks for safetensors first and errors out rather than falling back."""
    return any(Path(model_dir).glob("*/*.safetensors"))


def video_model_cfg() -> dict:
    return VIDEO_MODELS.get(os.environ.get("GENAI_VIDEO_MODEL", "5b").strip().lower(), VIDEO_MODELS["5b"])
KONTEXT_DIR = "/home/genai/genai/models/flux1-kontext-dev"

# Two quality tiers - both measured directly on this hardware (with VAE
# tiling, alongside Ollama's own VRAM usage):
#   480p (848x480): ~8.9s/frame
#   720p (1280x704): ~13.3s/frame - real 720p, noticeably sharper, slower
VIDEO_RESOLUTIONS = {
    "480p": (480, 848),
    "720p": (704, 1280),
    "1080p": (1088, 1920),
    # Portrait, for social and phone-first ads. Generating in the target shape
    # beats cropping a landscape clip, which throws away the sides and wrecks
    # whatever composition the model produced.
    "480p_v": (848, 480),
    "720p_v": (1280, 704),
    "1080p_v": (1920, 1088),
}
# Each model's native rate, from its own model card: TI2V-5B is documented as
# 720P@24fps, and the A14B line is 16fps. This is not a free choice - the frame
# count IS the motion duration, so exporting at the wrong rate plays the clip
# at the wrong speed. It used to be 8 for both, which made every video run at
# half (A14B) or a third (5B) of the intended speed.
VIDEO_FPS = 16

# Matches creative.py's ASPECTS, rounded to multiples of 16 (FLUX's VAE
# needs that) so the real generator's output matches what the stub promised.
ASPECT_SIZES = {
    "1:1": (768, 768),
    "16:9": (960, 544),
    "9:16": (544, 960),
    "4:3": (800, 608),
}

STYLE_SUFFIXES = {
    "Cinematic": "cinematic lighting, dramatic composition, film still",
    "Noir": "black and white, high contrast noir lighting, moody shadows",
    "Gold hour": "warm golden hour lighting, soft glow",
    "Raw": "raw unedited photo, natural lighting, candid",
    "Documentary": "documentary photography style, natural and authentic",
    "Ink": "ink illustration style, bold linework, monochrome",
}

_gpu_lock = threading.Lock()  # one GPU - serialize generations (image AND video share it)

# Single user, one job at a time: whichever workload is running owns the whole
# GPU, and everything else is evicted. Offload level per workload is tunable
# because the right answer depends on how much VRAM the chat model leaves free:
#   sequential - streams weights layer by layer. Lowest VRAM, brutally slow.
#   model      - moves whole components on demand. The safe middle.
#   none       - everything resident on GPU. Fastest, needs the card to itself.
# FLUX/Kontext are ~12B plus text encoders (over 24GB), so they can never reach
# "none" on this card. Wan is 5B and can, once chat stops squatting on the GPU.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

OFFLOAD_MODES = ("none", "model", "sequential")
IDLE_UNLOAD_SECONDS = int(os.environ.get("GENAI_IDLE_UNLOAD", "300"))

_PIPES = {}
_LAST_USED = {}
_LOADING = None  # which workload is loading right now, for the client's spinner
_PROGRESS = {"step": 0, "total": 0}  # live denoise progress, for a real progress bar


def offload_mode(kind: str, default: str) -> str:
    mode = os.environ.get(f"GENAI_OFFLOAD_{kind.upper()}", default).strip().lower()
    return mode if mode in OFFLOAD_MODES else default


def apply_offload(pipe, mode: str):
    if mode == "sequential" and getattr(pipe, "transformer", None) is not None and \
            getattr(pipe.transformer, "quantization_method", None) is not None:
        # Pre-quantized (bitsandbytes) weights cannot be streamed layer by
        # layer - it fails with "Cannot copy out of meta tensor". Fall back
        # rather than erroring at generation time.
        print("Sequential offload unsupported for a quantized model; using model offload.")
        mode = "model"
    if mode == "sequential":
        pipe.enable_sequential_cpu_offload()
    elif mode == "model":
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")
    return pipe


def unload(kind: str):
    """Caller must hold _gpu_lock, or be certain no generation is running."""
    pipe = _PIPES.pop(kind, None)
    _LAST_USED.pop(kind, None)
    if pipe is None:
        return
    del pipe
    gc.collect()
    torch.cuda.empty_cache()
    print(f"Unloaded {kind} pipeline, VRAM released.")


def release_chat_model():
    """Claim the GPU before generating. Done here rather than in the caller so
    it holds no matter who hits this service - a direct call to /generate_video
    used to OOM because only the Main API knew to evict chat first."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/ps", timeout=5) as r:
            loaded = json.loads(r.read().decode()).get("models", [])
    except Exception:
        return
    for m in loaded:
        name = m.get("model") or m.get("name")
        if not name:
            continue
        try:
            payload = json.dumps({"model": name, "prompt": "", "keep_alive": 0}).encode()
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate", data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=60).read()
            print(f"Evicted chat model {name} from GPU.")
        except Exception:
            pass
    if loaded:
        time.sleep(3)  # let the driver actually release the VRAM


def get_pipeline(kind: str, loader):
    global _LOADING
    release_chat_model()
    for other in list(_PIPES):
        if other != kind:
            unload(other)
    if kind not in _PIPES:
        _LOADING = kind
        try:
            _PIPES[kind] = loader()
        finally:
            _LOADING = None
    _LAST_USED[kind] = time.time()
    return _PIPES[kind]


def touch(kind: str):
    _LAST_USED[kind] = time.time()


def _load_edit_pipe():
    mode = offload_mode("edit", "model")
    print(f"Loading FLUX.1 Kontext-dev (offload={mode})...")
    pipe = FluxKontextPipeline.from_pretrained(KONTEXT_DIR, torch_dtype=torch.bfloat16)
    apply_offload(pipe, mode)
    print("Kontext loaded.")
    return pipe


def _load_image_pipe():
    mode = offload_mode("image", "model")
    print(f"Loading FLUX.1-schnell (offload={mode})...")
    pipe = FluxPipeline.from_pretrained(FLUX_DIR, torch_dtype=torch.bfloat16)
    apply_offload(pipe, mode)
    print("FLUX loaded.")
    return pipe


def _load_video_pipe(override: dict | None = None):
    mode = offload_mode("video", "model")
    cfg = override or video_model_cfg()
    print(f"Loading video model from {cfg['dir']} (offload={mode})...")
    # VAE must be float32 - bf16 produces garbage/noise output, confirmed
    # by direct testing before this was in place.
    st = uses_safetensors(cfg["dir"])
    vae = AutoencoderKLWan.from_pretrained(
        cfg["dir"], subfolder="vae", torch_dtype=torch.float32, use_safetensors=st
    )
    pipe = WanPipeline.from_pretrained(
        cfg["dir"], vae=vae, torch_dtype=torch.bfloat16, use_safetensors=st
    )
    for path, name, into_second in cfg.get("loras", []):
        # Wan 2.2 is a two-expert MoE; each expert takes its own LoRA.
        pipe.load_lora_weights(path, adapter_name=name, load_into_transformer_2=into_second)
        print(f"Applied LoRA {name}")
    if cfg.get("loras"):
        pipe.set_adapters([n for _, n, _ in cfg["loras"]])
    apply_offload(pipe, mode)
    # Without tiling, real 720p OOMs even with sequential offload - the
    # bottleneck is VAE decode activations, not weights. Confirmed by
    # direct testing: OOM'd at 720p until this was added.
    pipe.vae.enable_tiling()
    pipe.vae.enable_slicing()

    print("Wan 2.2 loaded.")
    return pipe


def get_edit_pipe():
    return get_pipeline("edit", _load_edit_pipe)


def get_pipe():
    return get_pipeline("image", _load_image_pipe)


def get_video_pipe(quality: bool = False):
    """Fast or quality, as two different models rather than one model tuned.

    The obvious approach - keep A14B and switch off its step-distillation
    LoRAs - does not work here, and the reason is worth recording. The A14B
    build is NF4 quantised, and removing a LoRA adapter makes diffusers
    dequantise the weights back to bf16 in order to strip it. That turns a
    14GB model into roughly 28GB of system RAM, and this machine has 30GB. It
    filled memory and the kernel killed the render, twice.

    So quality mode uses TI2V-5B instead: a smaller model that was never
    distilled, so it runs its full 20 steps with real guidance and at 24fps
    rather than 16. Fewer parameters, but every step is honest and the motion
    is smoother. On this hardware that is the better trade, and it was sitting
    in the config unused.
    """
    return get_pipeline("video_hq" if quality else "video",
                        _load_hq_video_pipe if quality else _load_video_pipe)


def model_fits_in_ram(model_dir: str) -> tuple[bool, float, float]:
    """(fits, weights GB, available GB).

    Checked before loading, because the failure mode otherwise is the kernel
    killing the process and taking the whole box into swap on the way. Weights
    on disk are a good proxy for what model-offload holds in RAM, and a third
    is left as headroom for activations and the runtime.
    """
    total = 0
    for f in Path(model_dir).rglob("*"):
        if f.is_file() and f.suffix in (".safetensors", ".bin", ".pth", ".ckpt"):
            total += f.stat().st_size
    weights = total / 1e9
    available = 0.0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                available = int(line.split()[1]) / 1e6
                break
    except Exception:
        return True, weights, 0.0      # cannot tell - do not block
    return weights * 1.3 <= available, weights, available


def _load_hq_video_pipe():
    cfg = VIDEO_MODELS["5b"]
    fits, weights, available = model_fits_in_ram(cfg["dir"])
    if not fits:
        raise RuntimeError(
            f"Quality mode needs about {weights * 1.3:.0f}GB of system RAM for "
            f"{weights:.0f}GB of weights, and only {available:.0f}GB is free. "
            f"This machine has 30GB and the board is full, so quality mode "
            f"cannot run here - it is a RAM limit, not a GPU one. Fast mode "
            f"(A14B NF4, 4 steps) is the only video config that fits."
        )
    return _load_video_pipe(cfg)


def _idle_reaper():
    """Hand the GPU back to Ollama when nothing has generated for a while."""
    while True:
        time.sleep(30)
        if IDLE_UNLOAD_SECONDS <= 0:
            continue
        cutoff = time.time() - IDLE_UNLOAD_SECONDS
        if not any(t < cutoff for t in _LAST_USED.values()):
            continue
        with _gpu_lock:
            for kind in [k for k, t in _LAST_USED.items() if t < cutoff]:
                unload(kind)


def safe_filename() -> str:
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}.png"


def build_prompt(prompt: str, style: str) -> str:
    suffix = STYLE_SUFFIXES.get(style, "")
    return f"{prompt}, {suffix}" if suffix else prompt


def nearest_valid_frame_count(n: int) -> int:
    """Wan wants num_frames = 4k+1. Round to the nearest valid value."""
    k = round((n - 1) / 4)
    return max(1, k * 4 + 1)


def set_vae_tiles(pipe, height: int) -> None:
    """VAE decode is the memory ceiling on a 24GB card. 1080p only fits with
    small tiles, but small tiles cost speed - so scale them to the job rather
    than penalising every resolution.
    """
    size = 192 if height >= 1000 else 256 if height >= 700 else 320
    for attr in ("tile_sample_min_height", "tile_sample_min_width"):
        if hasattr(pipe.vae, attr):
            setattr(pipe.vae, attr, size)


def save_frame(frame, path) -> None:
    """Pipelines disagree about frame type - the 5B hands back PIL images, the
    A14B hands back numpy arrays - so accept either rather than assuming."""
    if hasattr(frame, "save"):
        frame.save(path)
        return
    from PIL import Image

    arr = np.asarray(frame)
    if arr.dtype != np.uint8:
        arr = (arr.clip(0, 1) * 255).round().astype(np.uint8)
    Image.fromarray(arr).save(path)


def generate_video_bytes(prompt: str, style: str = "Cinematic", duration: int = 5, quality: str = "480p", steps: int | None = None, mode: str = "fast") -> bytes:
    cfg = video_cfg_for(mode)
    pipe = get_video_pipe(mode == "quality")
    full_prompt = build_prompt(prompt, style)
    height, width = VIDEO_RESOLUTIONS.get(quality, VIDEO_RESOLUTIONS["480p"])
    fps = int(cfg.get("fps", VIDEO_FPS))
    num_frames = nearest_valid_frame_count(max(1, min(duration, 25)) * fps)
    kwargs = {}
    if cfg.get("guidance_2") is not None:
        kwargs["guidance_scale_2"] = cfg["guidance_2"]
    filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.mp4"
    out_path = MEDIA_DIR / filename
    set_vae_tiles(pipe, height)
    total_steps = max(1, min(steps if steps else cfg["steps"], 40))

    def on_step(pipe_ref, i, t, cb_kwargs):
        _PROGRESS["step"] = i + 1
        _PROGRESS["total"] = total_steps
        return cb_kwargs

    with _gpu_lock:
        try:
            _PROGRESS.update({"step": 0, "total": total_steps})
            frames = pipe(
                prompt=full_prompt,
                height=height,
                width=width,
                num_frames=num_frames,
                num_inference_steps=total_steps,
                guidance_scale=cfg["guidance"],
                callback_on_step_end=on_step,
                **kwargs,
            ).frames[0]
            # Save the thumbnail BEFORE encoding. Encoding is the memory peak,
            # and doing this after it once failed with MemoryError, leaving a
            # good video with no preview image.
            poster = out_path.with_suffix(".png").name
            try:
                save_frame(frames[0], MEDIA_DIR / poster)
            except Exception as e:
                print(f"Poster extraction failed ({type(e).__name__}: {e}); no thumbnail.")
                poster = None
            export_to_video(frames, str(out_path), fps=fps)
        finally:
            del kwargs
            gc.collect()
            torch.cuda.empty_cache()
            _PROGRESS.update({"step": 0, "total": 0})
    touch("video")
    return out_path.read_bytes(), poster


def generate_image_bytes(prompt: str, style: str = "Cinematic", aspect: str = "1:1", steps: int = 4) -> bytes:
    pipe = get_pipe()
    width, height = ASPECT_SIZES.get(aspect, ASPECT_SIZES["1:1"])
    full_prompt = build_prompt(prompt, style)
    with _gpu_lock:
        try:
            image = pipe(
                full_prompt,
                width=width,
                height=height,
                guidance_scale=0.0,
                num_inference_steps=max(1, min(steps, 8)),  # schnell is tuned for very few steps
                max_sequence_length=256,
            ).images[0]
        finally:
            gc.collect()
            torch.cuda.empty_cache()
    touch("image")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    data = buf.getvalue()
    # also keep a copy on disk here for debugging/inspection
    (MEDIA_DIR / safe_filename()).write_bytes(data)
    return data


def edit_image_bytes(source_bytes: bytes, instruction: str, steps: int = 28) -> bytes:
    """Real edit takes ~19 minutes at 28 steps (measured) - genuinely slow,
    that's why this is only ever called from a background thread, never a
    live request."""
    pipe = get_edit_pipe()
    src_path = MEDIA_DIR / f"_edit_src_{uuid.uuid4().hex[:8]}.png"
    src_path.write_bytes(source_bytes)
    image = load_image(str(src_path))
    with _gpu_lock:
        try:
            result = pipe(
                image=image,
                prompt=instruction,
                guidance_scale=2.5,
                num_inference_steps=max(4, min(steps, 40)),
            ).images[0]
        finally:
            gc.collect()
            torch.cuda.empty_cache()
    touch("edit")
    src_path.unlink(missing_ok=True)
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    data = buf.getvalue()
    (MEDIA_DIR / safe_filename()).write_bytes(data)
    return data


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj, content_type="application/json", extra_headers=None):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {
                "status": "ok",
                "loaded": sorted(_PIPES),
                "loading": _LOADING,
                "busy": _gpu_lock.locked(),
                "progress": dict(_PROGRESS),
                "offload": {k: offload_mode(k, "model") for k in ("image", "video", "edit")},
                "idle_unload_seconds": IDLE_UNLOAD_SECONDS,
                "video_model": os.environ.get("GENAI_VIDEO_MODEL", "5b"),
            })
        if self.path.startswith("/media/"):
            name = self.path[len("/media/"):]
            if not re.fullmatch(r"[a-zA-Z0-9_.\-]+\.png", name):
                return self._send(400, {"error": "bad filename"})
            path = MEDIA_DIR / name
            if not path.exists():
                return self._send(404, {"error": "not found"})
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(path.stat().st_size))
            self.end_headers()
            self.wfile.write(path.read_bytes())
            return
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})

        if self.path == "/generate":
            # Matches Thunder-Main's creative.py forward_hook contract:
            # {prompt, style, aspect} in, raw PNG bytes out (forward_hook
            # wraps a non-JSON response as {"bytes": raw} automatically).
            prompt = (body.get("prompt") or "").strip()
            if not prompt:
                return self._send(400, {"error": "missing prompt"})
            try:
                png_bytes = generate_image_bytes(
                    prompt,
                    style=body.get("style", "Cinematic"),
                    aspect=body.get("aspect", "1:1"),
                    steps=body.get("steps", 4),
                )
                return self._send(200, png_bytes, content_type="image/png")
            except Exception as e:
                return self._send(500, {"ok": False, "error": str(e)})

        if self.path == "/generate_video":
            # Called from Main's background thread, not directly from a
            # user-facing request - this can legitimately take minutes.
            prompt = (body.get("prompt") or "").strip()
            if not prompt:
                return self._send(400, {"error": "missing prompt"})
            try:
                mp4_bytes, poster = generate_video_bytes(
                    prompt,
                    style=body.get("style", "Cinematic"),
                    duration=body.get("duration", 5),
                    quality=body.get("quality", "480p"),
                    steps=body.get("steps"),
                    mode=body.get("mode", "fast"),
                )
                return self._send(
                    200, mp4_bytes, content_type="video/mp4",
                    extra_headers={"X-Poster": poster} if poster else None,
                )
            except Exception as e:
                return self._send(500, {"ok": False, "error": str(e)})

        if self.path == "/edit":
            # Also only ever called from a background thread - ~19 min/edit.
            import base64

            instruction = (body.get("instruction") or "").strip()
            image_b64 = body.get("image_b64") or ""
            if not instruction or not image_b64:
                return self._send(400, {"error": "missing instruction or image_b64"})
            try:
                source_bytes = base64.b64decode(image_b64)
                png_bytes = edit_image_bytes(source_bytes, instruction, steps=body.get("steps", 28))
                return self._send(200, png_bytes, content_type="image/png")
            except Exception as e:
                return self._send(500, {"ok": False, "error": str(e)})

        return self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=_idle_reaper, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Thunder genai server listening on :{PORT}")
    server.serve_forever()
