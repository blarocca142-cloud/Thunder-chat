# Thunder desktop (private)

Chat + Studio on a PC. More room than the phone: model picker, file drag-drop, extra windows, logs, folder export.

No public GitHub Release. Download the private Actions artifacts, or run from this folder.

## Download

Private GitHub Actions artifacts (this PR / workflow **Build Thunder Desktop**):

- Linux: `thunder-desktop-linux` → `Thunder-0.8.2-linux-x64.AppImage`
- Windows: `thunder-desktop-windows` → `Thunder-0.8.2-windows-portable.exe` (and a zip)

Cursor copies, when this agent built them:

- `/opt/cursor/artifacts/Thunder-0.8.2-linux-x64.AppImage`
- `/opt/cursor/artifacts/Thunder-0.8.2-windows-portable.exe`

## Linux

```bash
chmod +x Thunder-0.8.2-linux-x64.AppImage
./Thunder-0.8.2-linux-x64.AppImage
```

If the AppImage asks for FUSE and your box is locked down:

```bash
./Thunder-0.8.2-linux-x64.AppImage --appimage-extract
./squashfs-root/thunder-desktop
```

## Windows

Double-click `Thunder-0.8.2-windows-portable.exe`. No installer. It is a portable app — put the exe anywhere and run it.

Or unzip the zip and run `Thunder.exe`.

## First run — point it at Main

1. Thunder opens. Left sidebar: **Main URL**.
2. Leave `http://127.0.0.1:8080` if the API is on this same PC.
3. If Main is the tower: `http://<MAIN-LAN-IP>:8080` — same Wi-Fi, firewall allows 8080.
4. Press Enter. Status pill should flip to `main`.
5. Tray (or the Thunder menu) → **Main URL…** also sets this. New windows pick it up.

Main must be running:

```bash
cd Thunder-chat-v3/thunder-main-api
python -m uvicorn app:app --host 0.0.0.0 --port 8080
```

## What desktop can do that the phone does not

- Power rail: switch the live model, queue/cancel overnight jobs, read logs
- Drag files onto the composer, or **Drop / review file**
- **New window** / tray **New chat window**
- **Export studio folder** (posters + ready clips)
- Studio video is async: poster first, polls Main every ~5s, Play when `video_status` is done

## Run from source (if you skip the binary)

```bash
cd Thunder-chat-v3/thunder-desktop
npm install
npm start
```
