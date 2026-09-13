# Thunder-chat v3

Local Thunder: chat plus a creative studio. Phone, browser, and desktop all talk to the same FastAPI on Main.

- `thunder-main-api/` — FastAPI on port **8080**. Chat hits local Ollama. Studio stubs until you hook a generator.
- `thunder-android/` — Kotlin app. Chat, saved chats, **Studio** tab (photo / video / history).
- `thunder-web/` — browser client (chat + studio). Served by the API at `/`.
- `thunder-desktop/` — Electron shell around the web client. Model picker, logs, file review, tray, extra windows.

Launcher icon is the exact user PNG. Do not remap or lighten it.

## Run Main API

```bash
cd Thunder-chat-v3/thunder-main-api
python3 -m pip install -r requirements.txt
# PowerShell: $env:THUNDER_MODEL="qwen2.5-coder:14b"
export THUNDER_MODEL=qwen2.5-coder:14b
python3 -m uvicorn app:app --host 0.0.0.0 --port 8080
```

Or `./run.sh`. Allow inbound TCP 8080 on the tower.

Phone gear → Server URL = `http://<MAIN-LAN-IP>:8080`.

Browser: open `http://<MAIN-LAN-IP>:8080`.

## Run the web client

With the API up, the real UI is already at `/`. You can also open `thunder-web/index.html` and paste the Main URL in the sidebar.

Same-origin (API serving the page) can leave the URL blank.

## Run desktop

Needs Node 20+ and the API running (or it falls back to the local web files).

```bash
cd Thunder-chat-v3/thunder-desktop
npm install
npm start
```

Desktop extras (not on the phone): model picker, Main logs, overnight job queue, file review, drag-drop into chat, extra windows, tray, `Ctrl/Cmd+Shift+T` to focus, `Ctrl/Cmd+1` chat, `Ctrl/Cmd+2` studio, folder export of stills.

## API contract (do not break Android chat)

```
GET  /status          → { mode, odriss, cache, ollama, model, job_id, job_title, progress, message, state }
POST /chat            body { "message" }           → { "reply" }
POST /job             body { "title", "prompt" }
POST /job/cancel      body { "job_id" }
```

Optional extras (new clients):

```
POST /chat            may also send { "messages": [{ "role", "content" }] } for longer desktop context
GET  /models          → { current, models[] }
POST /model           body { "model" }
GET  /logs            → { lines[] }
POST /image           body { "prompt", "style?", "aspect?" }  → creation record + /media/…
POST /video           body { "prompt", "style?", "duration?" } → poster stub until a renderer exists
GET  /creations       → { items[] }
GET  /media/{file}    → still / poster bytes
```

CORS is open. Android uses cleartext so `http://` LAN works.

## Studio stubs (plug real generators later)

`POST /image` and `POST /video` always accept the same JSON.

| Env | What happens |
|-----|----------------|
| unset | Thunder paints a studio still/poster and stores it under `thunder-data/creations/`. `stub: true`. |
| `THUNDER_IMAGE_URL` | POST the same JSON to that worker. If it returns image bytes, JSON `{image_b64}`, or `{url}`, Thunder saves that. |
| `THUNDER_VIDEO_URL` | POST the same JSON. If it returns `{video_url}`, that is stored. Poster is still saved for the gallery. |

No public GitHub Releases. Phone APK is the private Actions artifact `thunder-debug-apk` only.

## First test (no towers needed)

1. `python3 -m pip install -r thunder-main-api/requirements.txt`
2. `python3 -m uvicorn app:app --host 127.0.0.1 --port 8080` from `thunder-main-api/`
3. Open `http://127.0.0.1:8080`, send hello (Ollama optional — fallback still replies).
4. Studio → Photo → generate. You should get a stub still in History.
