# Thunder private debug keystore

Sideload-only. Same certificate on every GitHub Actions / cloud `assembleDebug` so new APKs **install over** the old app.

| | |
|---|---|
| File | `thunder-debug.keystore` (PKCS12) |
| Store password | `thunder-debug` |
| Key alias | `thunder` |
| Key password | `thunder-debug` |
| Cert SHA-256 | `C5:90:A7:87:63:E5:3E:5D:8A:F5:BE:6C:B5:B7:CA:7F:0A:EA:58:28:7F:AA:4B:89:19:53:A1:11:92:40:A9:EE` |

Not a Play Store upload key. Do not rotate unless every phone must uninstall Thunder first.
