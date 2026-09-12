# Wire Thunder into this Android app

The APK is a client. You implement the server on **Thunder-Main**.

Listen on `0.0.0.0:8080` (Tailscale interface is enough). Implement:

- `GET /status` → see README.md
- `POST /chat` `{message}` → `{reply}`  (call local Ollama here)
- `POST /job` `{title, prompt}` → write job file to Serverus, return `{job_id, status}`
- `POST /job/cancel` `{job_id}`

Do not change the Android package unless the JSON keys change. If you change keys, update `ThunderApi.kt`.

User is solo. One job at a time. `/chat` is Main 3090. `/job` is Cache.
