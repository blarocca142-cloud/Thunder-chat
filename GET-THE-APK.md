# Thunder APK — no Android Studio sync needed

The missing `gradle-wrapper.jar` is a binary. GitHub file tools cannot store it as text. GitHub Actions downloads it and builds the APK for you.

## Get the APK

1. Open https://github.com/blarocca142-cloud/Thunder-chat/actions
2. Click **Build Thunder APK**
3. Click **Run workflow** → **Run workflow**
4. Wait until the green check appears
5. Open that run → **Artifacts** → download **thunder-debug-apk**
6. Unzip it. Install `app-debug.apk` on the phone (allow unknown sources)

The first run can take 5–10 minutes.

## Install over the app already on the phone

`applicationId` is always `com.thunder.app`. Version numbers only go up.

From **0.8.5 onward**, every private APK is signed with the same Thunder keystore in `Thunder-chat-v3/thunder-android/keystore/`. Install the new APK on top of the old one. You should **not** have to uninstall.

### If the phone says signatures don’t match / package conflict

That is the old debug key from a random CI machine (pre-0.8.5). Uninstall Thunder **once**, then install 0.8.5+. After that, updates should overlay.

Settings → Apps → Thunder → Uninstall, then open `app-debug.apk` again.

## If you still want Android Studio later

Run this once in PowerShell:

```powershell
cd C:\Users\blaro\Thunder-chat\Thunder-chat-v3\thunder-android
.\GET-WRAPPER.ps1
```

Then File → Open that same `thunder-android` folder. Do not hunt for a Sync button.
