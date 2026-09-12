# Thunder Android

Phone front door for Thunder. One user. Talks only to **Thunder-Main**.

## What this app does (v1)

- Chat with Thunder
- See Odris status (`ok` / `stuck` / `no heartbeat`)
- Queue an overnight job
- Cancel the active job
- Switch mode display: `code` | `idle` (ad later)

The phone never SSHs Cache / Serverus / Odris.

## Open and install

1. Install [Android Studio](https://developer.android.com/studio)
2. File → Open → this `thunder-android` folder
3. Let Gradle sync
4. Run on a phone or emulator

First launch: set **Server URL**  
Example Tailscale: `http://thunder-main:8080`  
Example LAN: `http://192.168.1.50:8080`

## API Claude / Thunder must implement on Main

All JSON. CORS not required for the native app.

### `GET /status`

```json
{
  "mode": "code",
  "odriss": "ok",
  "cache": "running",
  "job_id": "job_20260912_0045",
  "job_title": "15s runner skeleton",
  "progress": "3/8 files",
  "last_write_unix": 1757650000,
  "message": "Cache heartbeat 40s ago"
}
```

`odriss`: `ok` | `stuck` | `no_heartbeat`  
`mode`: `code` | `idle` | `ad`  
`cache`: `idle` | `running` | `down`

### `POST /chat`

```json
{ "message": "add a stop-and-flag after 3 failed attempts" }
```

Response:

```json
{ "reply": "On it. I'll write the guard into the Cache worker." }
```

### `POST /job`

```json
{ "title": "overnight: four-tool loop", "prompt": "implement the job runner..." }
```

Response:

```json
{ "job_id": "job_20260912_0045", "status": "queued" }
```

### `POST /job/cancel`

```json
{ "job_id": "job_20260912_0045" }
```

Response: `{ "status": "cancelled" }`

Until these exist, the app uses **demo mode** (fake replies + fake Odris) so you can tap through the UI.

## 12:45 split

- **This repo:** Android UI + API client (done)
- **Claude / you on Main:** FastAPI (or similar) on `:8080` exposing the four routes, talking to Ollama + Serverus + Odris `status.json`

Do not put Ollama on the phone.
