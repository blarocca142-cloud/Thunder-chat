# Thunder Android

Phone app: Chat tab (saved chats drawer) and Studio tab (photo / video / history).

Build the private APK with GitHub Actions (`thunder-debug-apk`). Do not publish a Release.

Gear → Server URL = `http://MAIN-LAN-IP:8080`. Empty URL is shell mode. Chat and Studio still open.

## Claude

Read `CLAUDE.md`. Do not rebuild the UI first. Wire `/chat` and `/status` on Main, then point the app at `http://MAIN-TAILSCALE-IP:8080`.
