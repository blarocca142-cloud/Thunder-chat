# Claude — wire Thunder into this Android app

The APK is a client shell. It already launches.

Your job:
1. The UI is being revamped at Blayne's request (2026-09-27): replies render through `ui/ReplyRender.kt`.
2. Point Settings → Server URL at Thunder-Main (`http://IP:8080`).
3. Confirm these endpoints on Main:
   - GET /status
   - POST /chat  body `{ "message": "..." }`  returns `{ "reply": "..." }`
   - POST /job   body `{ "title", "prompt" }`
   - POST /job/cancel body `{ "job_id" }`
4. If JSON keys change, edit `app/src/main/java/com/thunder/app/data/ThunderApi.kt` only.

User is solo. One job at a time. Chat = Main GPU. Overnight code = Cache later.
