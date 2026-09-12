# HANDOFF FOR CLAUDE — Thunder
Owner: Blayne (blarocca142-cloud). Solo. One user. One job at a time.
Repo: https://github.com/blarocca142-cloud/Thunder-chat
Use **Thunder-chat-v3 only**. Ignore v1 and v2 folders.

## What Thunder is
Local AI so Blayne is not blocked when Grok/Claude usage is maxed.
Chat + vibe-code like Grok. Later: overnight coding loop, then 15s auto-injury ad videos (one-shot, no stitching clips).
This is NOT a Grok clone. It is Thunder. Dark chat UI is inspired by Grok but must stay legally distinct (name, colors, wordmark).

## What is DONE (2026-09-12)
- Native Android app on Blayne's real phone. Looks good. Sideloaded debug APK (not Play Store).
- Package: `com.thunder.app`. Version 0.2.0.
- UI: `Thunder-chat-v3/thunder-android/app/src/main/java/com/thunder/app/ui/ThunderRoot.kt`
  - Dark chat, bubbles, empty state "What do you want to work on?"
  - Gear icon → Server URL (leave empty = shell mode)
  - Status pill: `shell` vs `main`
- API client: `.../data/ThunderApi.kt`
  - POST `{server}/chat` body `{ "message" }` expects `{ "reply" }`
  - GET `{server}/status`
- FastAPI on Main: `Thunder-chat-v3/thunder-main-api/app.py` port **8080**
  - GET `/` tiny HTML chat
  - GET `/status`
  - POST `/chat` → Ollama `/api/chat` if up, else fallback string
  - POST `/job` and POST `/job/cancel` (files on disk, no worker yet)
- GitHub Actions builds the APK: `.github/workflows/build-apk.yml`
  - Artifact name: `thunder-debug-apk`
  - Workflow downloads `gradle-wrapper.jar` at build time (binary is not in git)
- Ollama on the Windows laptop is installed (0.34.0). The 32b model was **deleted** because it ate ~20GB and 500'd on the laptop.
- Android Studio is installed but Blayne hates it. Do not send him hunting Sync. Build APK via Actions.

## What is NOT done — this is YOUR job tomorrow
1. Run Thunder-Main API on the **Main tower**, not the laptop.
2. Pull a model that fits the 3090. Do **not** default to `qwen2.5-coder:32b` on the laptop. On Main with 3090, 32b may work; if VRAM is tight use `qwen2.5-coder:14b` or `7b` and set `THUNDER_MODEL`.
3. Make the phone actually talk to Main:
   - Phone and Main on same Wi-Fi
   - Gear → Server URL = `http://<MAIN-LAN-IP>:8080`
   - Send "hello" → real model reply, not shell fallback
4. Persist the Server URL (SharedPreferences). Right now it dies when the app is killed.
5. Optional: Odris heartbeat writing `thunder-data/status.json` so the pill is real.
6. Do NOT start overnight Cache loop, video gen, game engine, or Play Store until chat works end-to-end on the phone.

## Hardware (everything serves Thunder)
- **Thunder-Main**: 2013 ThinkCentre P93, RTX 3090, RAM already maxed. Chat GPU. Keep this free for Blayne during the day.
- **Serverus**: Thunder's memory (conversations, scene facts). Not wired yet.
- **Thunder-Cache**: overnight coding worker. Not wired yet.
- **Thunder-Engine**: cheap CPU router / safety yes-no. Not wired yet.
- **Odris**: watches Cache + Serverus, reports through Thunder. SSH monitor, no GPU required. Not wired yet.
- Adding a P40 later is extra GPU on Main. Not required for chat.

## API contract (do not break the Android client)
```
GET  /status
  → { mode, odriss, cache, ollama, model, job_id, job_title, progress, message, state }

POST /chat
  body { "message": "..." }
  → { "reply": "..." }

POST /job
  body { "title", "prompt" }
  → queued job record

POST /job/cancel
  body { "job_id" }
```
CORS is open. `usesCleartextTraffic=true` so http:// LAN works.
If you change JSON keys, also edit `ThunderApi.kt`.

## Run Main (on the tower, not laptop)
```
cd Thunder-chat-v3/thunder-main-api
python -m pip install -r requirements.txt
set THUNDER_MODEL=qwen2.5-coder:14b   # or 32b if 3090 holds it
ollama serve
ollama pull %THUNDER_MODEL%
python -m uvicorn app:app --host 0.0.0.0 --port 8080
```
Windows PowerShell: `$env:THUNDER_MODEL="qwen2.5-coder:14b"`
Firewall: allow inbound TCP 8080.

## Build a new APK without Android Studio
Push to `main` under `Thunder-chat-v3/thunder-android/**`
OR run workflow "Build Thunder APK" on GitHub Actions.
Download artifact `thunder-debug-apk` → install `app-debug.apk` over the existing app.

## How Blayne works
- Baby steps. One click at a time. No assumed menus.
- He is on a phone a lot. Prefer GitHub + APK over Studio.
- Do not copy-paste walls of code at him unless he asks. You have repo write.
- Chat quality should feel like talking to Grok: direct, useful, not a chatbot toy.
- Ads / video / game engine are later. Chat on the phone is the gate.

## Success for tomorrow
Phone app, gear set to Main IP, send a message, Thunder (Ollama on the 3090) replies. That is the whole win.
