# Thunder-chat v3

Write access is live. This is the first real push from Grok.

- `thunder-main-api/` — FastAPI on Main, port 8080. `/chat` hits local Ollama. Jobs, maintenance, Odris/Serverus/Engine stay. Studio stubs: `/image`, `/video`, `/creations`.
- `thunder-android/` — Chat | Studio tabs, saved chats, locked user-PNG launcher, maintenance banner.
- `thunder-web/` — browser client at `/` (chat + studio). Same API.
- `thunder-desktop/` — Electron shell around the web client (model picker, logs, files, tray).

## Run Main API

```bash
cd Thunder-chat-v3/thunder-main-api
python3 -m pip install -r requirements.txt
python3 -m uvicorn app:app --host 0.0.0.0 --port 8080
```

Or `./run.sh`.

Browser: `http://MAIN-IP:8080`. Phone gear → that same URL.

Desktop:

```bash
cd Thunder-chat-v3/thunder-desktop
npm install
npm start
```

Studio hooks (optional): `THUNDER_IMAGE_URL`, `THUNDER_VIDEO_URL`. Unset = stub still/poster saved under `thunder-data/creations/`. No public GitHub Releases — APK is the private Actions artifact `thunder-debug-apk`.

## First test (no towers needed)

1. Install Ollama on the laptop or Main.
2. `ollama pull mistral-small:24b` (or whatever `THUNDER_MODEL` you've set — no Qwen/Alibaba models)
3. Run the API.
4. Open the web UI, send "hello".
