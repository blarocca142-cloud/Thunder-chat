# Thunder Android (shell)

This is the phone app. It is supposed to open and look like Thunder even if Main is offline.

Open this folder in Android Studio → Run on a phone or emulator → Build → Generate Signed Bundle / APK if you want an APK.

Default server URL is empty. Chat still works in demo mode until Claude wires Main.

## Claude

Read `CLAUDE.md`. Do not rebuild the UI first. Wire `/chat` and `/status` on Main, then point the app at `http://MAIN-TAILSCALE-IP:8080`.
