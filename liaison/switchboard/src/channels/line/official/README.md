---
name: line-official
description: "LINE 官方帳號 channel：Messaging API，webhook inbound + push/reply outbound。"
---

# LINE 官方帳號 Channel

## 運作原理

使用 LINE Messaging API，需申請 LINE Official Account：
- **Inbound**：LINE platform 將訊息 POST 至 webhook endpoint
- **Outbound**：呼叫 push/reply message API 發送訊息

## Secrets

| Secret | get-secret.sh name | 交付 env var |
|--------|-------------------|--------------|
| Channel Secret | `line-official-channel-secret` | `LINE_OFFICIAL_CHANNEL_SECRET` |
| Channel Access Token | `line-official-channel-token` | `LINE_OFFICIAL_CHANNEL_TOKEN` |

填入方式（本地）：
```bash
echo "your-channel-secret" > ~/.logos/secrets/line-official/channel-secret
echo "your-channel-access-token" > ~/.logos/secrets/line-official/channel-access-token
```

## 設定精靈

```bash
uv run setup.py [--provider NAME] [--channel NAME] \
                [--email EMAIL] [--webhook-url URL] \
                [--qr-port PORT]
```

未提供參數時會互動式詢問。步驟：
1. 啟動 headless 瀏覽器
2. 登入 LINE Developers Console（QR code 掃描，備用圖片開 `http://<ip>:8889/`）
3. 建立或選取 Provider 與 Messaging API Channel
4. 取得並儲存 Channel Secret & Channel Access Token
5. 設定 Webhook URL（可選，稍後補設亦可）

## 檔案結構

| 檔案 | 職責 |
|------|------|
| `setup.py` | 設定精靈主流程（協調各模組） |
| `login.py` | 登入 LINE Developers Console（QR 顯示與等待） |
| `console.py` | Provider + Messaging API Channel 建立與憑證提取 |
| `webhook.py` | Webhook URL 設定、啟用、驗證 |
| `credentials.py` | Channel Secret & Token 儲存/讀取 |

## 模組狀態

| 功能 | 狀態 |
|------|------|
| 設定精靈（setup） | ✅ `setup.py` |
| Console 登入（QR） | ✅ `login.py` |
| Provider + Channel 建立 | ✅ `console.py` |
| Webhook 設定 | ✅ `webhook.py` |
| 憑證管理 | ✅ `credentials.py` |
| Webhook server（inbound） | ⬜ 待建立 |
| Push message（outbound） | ⬜ 待建立 |
| Signature 驗證 | ⬜ 待建立 |

## 注意事項

`console.py` 的 CSS selector 基於 LINE Developers Console 2024/2025 版面。
若 UI 更新導致自動化失效，請依實際 DOM 調整 selector，主要位於
`_ensure_provider`、`_ensure_messaging_api_channel`、`_extract_credentials` 函式。
