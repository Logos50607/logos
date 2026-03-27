# DEPENDENCIES

## Python

| 套件 | 版本需求 | 用途 | 安裝指令 |
|------|----------|------|----------|
| playwright | >=1.40 | CDP 連接 Chrome，攔截 LINE extension service worker 流量 | `pip install playwright && playwright install chromium` |
| pillow | - | 影像處理（QR code 解碼用） | uv 自動安裝（login.py inline dep） |
| zxing-cpp | - | QR code 解碼（從 canvas 擷取 LINE QR data） | uv 自動安裝（login.py inline dep） |
| qrcode | - | Terminal QR code ASCII 顯示 | uv 自動安裝（login.py inline dep） |

## Secrets（透過 internal-control）

| Secret | 用途 | 取用方式 |
|--------|------|----------|
| `line-personal-session` | LINE Chrome session 目錄 | `get-secret.sh line-personal-session liaison/switchboard` |
| `line-official-channel-secret` | LINE Messaging API 驗證 | `get-secret.sh line-official-channel-secret liaison/switchboard` |
| `line-official-channel-token` | LINE Messaging API 發送 | `get-secret.sh line-official-channel-token liaison/switchboard` |
