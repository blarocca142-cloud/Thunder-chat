# Thunder Turbo and Thunder Deep

## Turbo: llama-server for the main model

`app.py` uses llama.cpp's `llama-server` for the main model when
`THUNDER_BACKEND=llamacpp` and it answers on `THUNDER_LLAMACPP_URL`
(default :8081); otherwise, and always for the medical model, Ollama. Same
tool loop, same guards - `agent.py` speaks both wire formats.

    ./turbo.sh model qwen3:32b                       # find the GGUF Ollama already has
    sudo ./turbo.sh install qwen3:32b qwen3:0.6b     # target + same-family draft

It runs as the `ollama` user, so the egress lockdown covers it too.

### What was measured here (CPU container, Qwen2.5 1.5B target, 0.5B draft)

- **Real end to end**: the model chose `run_python` on its own, the call went
  through the real gate code into the sandbox, and it answered 17*23+5 = 396.
- **Every speculative mode produced output identical to plain decoding.**
- **Speed on CPU: no gain.** draft-simple 0.34-0.69x (the draft costs more CPU
  than it saves); ngram-mod / ngram-simple / ngram-cache 0.86-1.00x on prompts
  they had not seen.
- A first run showed ngram-mod at **4.5x - that was fake**: the warm-up used the
  same prompt and the n-gram cache replayed it. `turbo_bench.py` warms up on a
  different prompt for that reason.

On the 3090 the draft model runs on the GPU beside the target and costs a
fraction of what it does on CPU, which is where draft-simple is expected to
pay. **Unproven until `turbo_bench.py` says so on Main.** If it does not pay,
leave `THUNDER_BACKEND=ollama`.

This llama.cpp defaults to `--spec-type none`: without naming a type, a loaded
draft model is silently unused. turbo.sh names it.

One GPU, two big models: Turbo holds the main model's VRAM permanently, so a
separate medical model on Ollama cannot also sit on the GPU. If the shootout's
winner is non-Chinese it can serve both roles and the problem disappears;
otherwise medical requests are slower while Turbo is up.

## Deep: a mixture-of-experts model spread over the fleet

`deep_plan.py` reads a MoE GGUF (e.g. gpt-oss-120b: ~117B total, ~5B active
per token) and each node's free RAM, and writes the llama-server command that
keeps attention on the 3090 and places whole layers of experts in the RAM of
Main, serverus and thunder-engine via `-ot ...=RPC[host:port]` / `=CPU`.

Dense models split across the fleet measured 55.5 -> 1.8 tok/s (8dc686a)
because every layer's weights were read by old CPUs. MoE reads only the
active experts per token, which is why this is worth measuring - not a promise
of speed. It is a way to run a model bigger than any single machine; expect it
to be slower than the 30B on the GPU and use it as deep mode / overnight.

`rpc-server` has no authentication: bind it to the LAN address and firewall it
to Main (10.168.168.10) only, and stop it when not in use.
