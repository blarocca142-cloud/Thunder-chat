# Thunder-chat v3

Write access is live. This is the first real push from Grok.

- `thunder-main-api/` — FastAPI on Main, port 8080. `/chat` hits local Ollama, falls back if it's down. `/status`, `/job`, `/job/cancel`.
- `thunder-android/` — Kotlin app (chat, Odris pill, queue/cancel).
- `thunder-web/` — phone browser UI, same API.

## Run Main API

```bash
cd Thunder-chat-v3/thunder-main-api
python3 -m pip install -r requirements.txt
python3 -m uvicorn app:app --host 0.0.0.0 --port 8080
```

Or `./run.sh`.

Phone: open `thunder-web/index.html`, set URL to `http://MAIN-IP:8080`.

## First test (no towers needed)

1. Install Ollama on the laptop or Main.
2. `ollama pull qwen2.5-coder:32b`
3. Run the API.
4. Open the web UI, send "hello".
