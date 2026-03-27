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

## 模組狀態

| 功能 | 狀態 |
|------|------|
| Webhook server (inbound) | ⬜ 待建立 |
| Push message (outbound) | ⬜ 待建立 |
| Signature 驗證 | ⬜ 待建立 |
