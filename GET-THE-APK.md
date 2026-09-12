# Thunder APK — no Android Studio sync needed

The missing `gradle-wrapper.jar` is a binary. GitHub file tools cannot store it as text. GitHub Actions downloads it and builds the APK for you.

APKs are **private Actions artifacts only**. They require a GitHub login. Do not publish GitHub Releases or public `releases/download` links.

## Get the APK

1. Open https://github.com/blarocca142-cloud/Thunder-chat/actions
2. Open the latest **Build Thunder APK** run on this PR (or click **Run workflow**)
3. Wait for the green check
4. **Artifacts** → download **thunder-debug-apk** (GitHub login required)
5. Unzip and install `app-debug.apk` over the existing app (allow unknown sources)

The first run can take 5–10 minutes.

## If you still want Android Studio later

Run this once in PowerShell:

```powershell
cd C:\Users\blaro\Thunder-chat\Thunder-chat-v3\thunder-android
.\GET-WRAPPER.ps1
```

Then File → Open that same `thunder-android` folder. Do not hunt for a Sync button.
