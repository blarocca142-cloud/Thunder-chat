# Thunder APK — no Android Studio sync needed

The missing `gradle-wrapper.jar` is a binary. GitHub file tools cannot store it as text. GitHub Actions downloads it and builds the APK for you.

## Phone download (no GitHub login)

Tap this on the phone and install over the existing Thunder app (allow unknown sources):

https://github.com/blarocca142-cloud/Thunder-chat/releases/download/v0.4.1-thunder-face/Thunder-v0.4.1-thunder-face-debug.apk

Release page: https://github.com/blarocca142-cloud/Thunder-chat/releases/tag/v0.4.1-thunder-face

## Get a newer APK from Actions

1. Open https://github.com/blarocca142-cloud/Thunder-chat/actions
2. Click **Build Thunder APK**
3. Click **Run workflow** → **Run workflow**
4. Wait until the green check appears
5. Open that run → **Artifacts** → download **thunder-debug-apk**
6. Unzip it. Install `app-debug.apk` on the phone (allow unknown sources)

The first run can take 5–10 minutes.

## If you still want Android Studio later

Run this once in PowerShell:

```powershell
cd C:\Users\blaro\Thunder-chat\Thunder-chat-v3\thunder-android
.\GET-WRAPPER.ps1
```

Then File → Open that same `thunder-android` folder. Do not hunt for a Sync button.
