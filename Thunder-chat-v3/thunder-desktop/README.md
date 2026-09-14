# Thunder desktop

Electron shell around `thunder-web`. Same brand, more room than the phone.

See **[GET-DESKTOP.md](../GET-DESKTOP.md)** for private download, install, and first-run Main URL.

```bash
cd Thunder-chat-v3/thunder-desktop
npm install
npm start
```

Pack private binaries (no public GitHub Release):

```bash
npm run pack:linux   # AppImage
npm run pack:win     # portable exe + zip (best on Windows CI)
```

`Ctrl/Cmd+Shift+T` focuses Thunder from the tray. Tray → **Main URL…** points at the tower.
