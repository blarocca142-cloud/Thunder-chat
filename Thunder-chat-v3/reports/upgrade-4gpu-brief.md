# 4-GPU upgrade brief

Written 2026-09-29 so this stops being re-explained. Paste the "Brief for the
researcher" section into Grok (or anything else) to price out parts.

## Why Main cannot just take more cards

- Main is a Lenovo ThinkCentre M93p: Haswell i7-4790 on a Q87 SHARKBAY board.
  One real x16 slot, 4 DIMM slots maxed at 32GB DDR3. No upgrade path.
- So 4 GPUs means a **new platform**: board, CPU, RAM, PSU, case/frame. The
  current RTX 3090 carries over.
- Chat models *do* split across GPUs in one box (llama.cpp / vLLM tensor or
  layer split over PCIe). Across towers over the network it was measured 30x
  slower - that route is dead. Video/diffusion cannot split at all; it stays
  single-card (and is shelved anyway).

## What 4 x 24GB buys

96GB VRAM. Candidates, US/EU origin only (no Qwen/DeepSeek/GLM/etc. - Blayne's
rule, and never for medical):

- **gpt-oss-120b** (OpenAI, US) - ~65GB in its native MXFP4, fits with room for
  long context and several users at once. Same family as today's model, so the
  tool layer, guards and prompts carry over. The obvious first pick.
- Llama 3.3 70B (Meta, US) at Q8 (~75GB).
- Mistral Large-class (Mistral, France) at Q4 if a 120B+ dense model is wanted.

Pick by the same measured shootout as before, not by reputation.

## Brief for the researcher (paste this)

> I'm building a local AI server to run large language models (70B-120B) on
> 4x NVIDIA RTX 3090 24GB. I already own one 3090. US-based, budget-conscious,
> used/refurbished parts are fine. Please find current prices and specific
> models (with links) for:
>
> 1. **Motherboard + CPU** with enough PCIe lanes for 4 GPUs at x8 or better
>    (x16/x8/x8/x8 minimum). Good used options: AMD EPYC 7002/7003 (e.g. EPYC
>    7302/7402 + ASRock Rack ROMED8-2T or Supermicro H12SSL-i), Threadripper
>    Pro 3000/5000 (WRX80), or Intel Xeon W-2200/W-3200. Compare total cost.
> 2. **RAM**: 128GB minimum, 256GB preferred, ECC DDR4 matching the board.
> 3. **3 more RTX 3090s** (used, eBay/r/hardwareswap/local). Blower or 2-slot
>    models preferred; otherwise PCIe 4.0 riser cables. Current fair price range.
> 4. **Power**: 4x 3090 is ~1400W at stock. Recommend PSU(s): one 1600W+
>    80+ Platinum/Titanium, or two PSUs with an add2psu board. Assume cards will
>    be power-limited to ~250W each. Tell me whether a normal 15A/120V US
>    household circuit is enough at ~1,300W total draw, or if I need a
>    dedicated 20A circuit.
> 5. **Case/frame**: open-air mining frame vs. a server/workstation case that
>    fits 4 triple-slot cards, plus cooling.
> 6. **Storage**: 2TB NVMe for models.
>
> Give me 2 builds: a cheapest-that-works build and a recommended build, each
> with a parts list, per-part price, total, and total power draw. Flag any
> compatibility traps (slot spacing, riser generation, BIOS above-4G decoding /
> resizable BAR, PSU cable counts).

## Things to decide before buying

- Where it lives: 4x 3090 is loud and dumps ~1.3kW of heat into the room.
- Whether the new box replaces Main as the claims box (it should: the security
  setup - TLS, auth, vault, egress lockdown - moves with it, and Main becomes a
  spare).
- Budget. This is well past the under-$100 rule; expect several thousand
  dollars, most of it the three used 3090s.
