# Thunder Android (shell)

This is the phone app. It is supposed to open and look like Thunder even if Main is offline.

Open this folder in Android Studio → Run on a phone or emulator.

Private APKs from GitHub Actions are signed with `keystore/thunder-debug.keystore` so they install **over** the existing Thunder (from 0.8.5 on). See repo-root `GET-THE-APK.md`.

Default server URL is empty. Chat still works in demo mode until Main is pointed in Settings.

## Claude

Read `CLAUDE.md`. Do not rebuild the UI first. Wire `/chat` and `/status` on Main, then point the app at `http://MAIN-TAILSCALE-IP:8080`.
