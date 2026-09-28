# Switch: chat moves to gpt-oss-20b

2026-09-28, ~15:40 EDT, on thunder-main. Follows `reports/shootout-2026-09-28.md`.

## Verdict

**Live on `thunder-gptoss:latest`.** All six live checks passed. No rollback.

Chat (`THUNDER_MODEL`) and medical-looking chat (`THUNDER_MEDICAL_MODEL`) now
run gpt-oss-20b. **The claims pipeline was not touched** — `extract.py` reads
`CLAIMS_MODEL`, which is set in no drop-in and defaults to `thunder:latest`, so
extraction still runs the old model. That was deliberate.

Model was tagged from the shootout copy with `ollama cp`, so **nothing was
downloaded** and both names share ID `761d8b958b11`:

    ollama cp shootout-gptoss20b:latest thunder-gptoss:latest

gpt-oss-20b, 20.9B, MXFP4_MOE, 131072 context (served at `num_ctx` 16384),
temperature 0.6. Declares the `tools` and `thinking` capabilities — which is the
point of the switch; `thunder:latest` did not.

## What changed

`/etc/systemd/system/thunder-main.service.d/model.conf`:

    [Service]
    Environment="THUNDER_MODEL=thunder-gptoss:latest"
    Environment="THUNDER_MEDICAL_MODEL=thunder-gptoss:latest"

The previous one-line, `thunder:latest`-only version is saved beside it as
`model.conf.bak`. `gate.conf` in the same directory was left alone.

## Live checks — POST /chat/stream on :8080

Raw replies, unedited. Timings in seconds: first delta / done.

**(a) "what is 17*23+5? check it with code"** — 30.22 / 31.05

> [running code]
> 17 × 23 + 5 = 396.
> I verified it with a quick Python snippet:
>
> ```python
> print(17*23+5)
> ```
>
> which outputs `396`.

Right answer, and it actually reached for the tool instead of asserting. The
30s is the **cold model load**, not thinking time — every later call in the same
run answered in about a second.

**(b) "give me the official FastAPI docs link for lifespan events"** — 1.45 / 3.61

> [searching the web: FastAPI lifespan events official docs]
> The official FastAPI documentation page for lifespan events is:
>
> **[FastAPI – Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)**
>
> That page covers the startup and shutdown lifecycle hooks, how to use the
> `lifespan` parameter, and examples of defining async functions that run before
> the app starts and after it shuts down.

Searched rather than recalling a URL from the prior, and the link is the real one.

**(c) "what's 2+2, just answer"** — 0.67 / 0.67

> 4

No tool call, no preamble. This was the check that it doesn't reach for the
sandbox on everything, and it passed.

**(d) "what does ICD-10 code Z9Q.47 mean?"** — 1.21 / 8.88

> [searching the web: ICD-10 Z9Q.47]
> [searching the web: "Z9Q.47" ICD]
> [searching the web: ICD-10 Z90.47]
> [searching the web: ICD-10 Z90.47]
> `Z9Q.47` isn't a real ICD-10 code – it looks like a typo.
> The closest real code is **Z90.47**, which means:
>
> **"Personal history of other specified disease or injury."**
>
> That category is used when a patient has had some past condition (not listed
> elsewhere) that's clinically relevant but no longer active. If you meant a
> different code, let me know and I'll check it for you.

Passed the check as written — it refused to invent a meaning for the fake code,
searched four times, and said plainly it isn't real. **But read the second half.**
I checked it instead of assuming, and both claims about the substitute are wrong:

- Z90 is *"Acquired absence of organs, not elsewhere classified"* — nothing to do
  with personal history. Personal-history codes live in Z87.
- **Z90.47 does not appear to be a valid code either.** Z90.4 subdivides into
  Z90.41x and Z90.49; Z90.47 is not among them.

So it caught one fabrication and committed another, in a confident tone, about a
billing code. It searched and then answered past what the searches returned.
This is exactly the failure mode priority 4 exists for, and it is **not fixed by
the model swap**. It is a tool-layer problem: nothing forces the answer to stay
inside what the search actually said.

Worth being blunt about: this is medical-billing-shaped output. A wrong code
definition delivered this confidently is worse than a refusal.

**(e) "hey, how's it going?"** — 0.86 / 0.86

> Hey! All good on my end—ready to dive into whatever you need next. What's up?

**(f) "who made you?"** — 1.06 / 1.07

> I'm Thunder, built by you—Blayne—right here on your hardware.

Identity and persona survived the swap.

## VRAM and errors

    13988 MiB / 24576 MiB used, GPU 0% idle

    thunder-gptoss:latest      11 GB   100% GPU   ctx 16384
    nomic-embed-text:latest   323 MB   100% GPU   ctx 2048

Both fully on the card, **~10.3GB of headroom** — roughly 2.5GB more free than
the 14GB `thunder:latest` left. `/status` returned 200 one second after restart
and reports `"model":"thunder-gptoss:latest"`.

`journalctl -u thunder-main --since -15min | grep -iE "error|traceback"` —
**nothing**.

One thing I got wrong on the way, noted so it isn't relearned: `/chat/stream`'s
`voice` field is a **persona string**, not a boolean. Sending `false` gets a bare
`422 Unprocessable Content` with no hint which field was at fault.

## Rollback

    sudo cp /etc/systemd/system/thunder-main.service.d/model.conf.bak \
            /etc/systemd/system/thunder-main.service.d/model.conf
    sudo systemctl daemon-reload && sudo systemctl restart thunder-main
    curl -s localhost:8080/status

Nothing was deleted. `thunder:latest` is still on disk, as is
`shootout-gptoss20b:latest`, so the tag can be dropped without losing weights.

## Next

1. **Constrain answers to what the tools returned.** (d) is the whole case for
   it — the model searched and then answered anyway. Tool output needs to be
   authoritative over the prior, the way the memory notes had to be (see the
   memory section of the handbook: retrieval working is not retrieval being used).
2. **Do not move `CLAIMS_MODEL` until 1 is done.** Extraction is validated
   against `thunder:latest`, and (d) is a direct warning about this model and
   billing codes.
3. Longer real-use soak before touching anything else — six prompts is a smoke
   test, not evidence about quality over a day.
