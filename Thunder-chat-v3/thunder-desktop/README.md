# Thunder desktop

Electron shell around `thunder-web`. Same brand, more room than the phone.

```bash
# API first
cd ../thunder-main-api && python3 -m uvicorn app:app --host 127.0.0.1 --port 8080

# then
cd ../thunder-desktop
npm install
npm start
```

If Main is not on 8080, set the URL in the sidebar. `Ctrl/Cmd+Shift+T` focuses Thunder from the tray.

No public GitHub Release. Run it locally.
