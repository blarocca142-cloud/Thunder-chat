# Claude — wire Thunder into this Android app

The APK is a client shell. It already launches.

Your job:
1. Keep the UI.
2. Point Settings → Server URL at Thunder-Main (`http://IP:8080`).
3. Confirm these endpoints on Main:
   - GET /status
   - POST /chat  body `{ "message": "..." }`  returns `{ "reply": "..." }`
   - POST /job   body `{ "title", "prompt" }`
   - POST /job/cancel body `{ "job_id" }`
   - POST /image and POST /video (studio; stubs until hooks exist)
   - GET /creations and GET /media/{file}
4. If JSON keys change, edit `app/src/main/java/com/thunder/app/data/ThunderApi.kt` only.

User is solo. One job at a time. Chat = Main GPU. Overnight code = Cache later.
