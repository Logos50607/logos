---
name: line-personal-login
trigger: always_on
description: "LINE 個人帳號登入檢查規範：偵測未登入時引導使用者執行登入流程。"
---

# LINE 個人帳號登入規範

## 登入狀態檢查

任何需要讀取 LINE 個人帳號資料的操作前，必須先確認已登入。
判斷方式：連接 CDP 後，extension page URL hash 應為 `/friends`、`/chats` 等，
而非 `/`（登入頁）。

## 未登入時的處理

偵測到未登入時，**不得靜默失敗**，必須：

1. 告知使用者目前未登入
2. 引導執行登入流程：

```bash
uv run /data/logos/liaison/switchboard/src/channels/line/personal/run.py
```

3. 說明登入只能在 terminal 完成（需掃 QR code）

## 注意事項

- 登入 session 儲存在 `LINE_PERSONAL_SESSION` 路徑的 Chrome user-data-dir
- session 有效期約 30 天，過期需重新掃 QR
- 登入流程需要 Xvfb（headless display）與 Chrome，`run.py` 會自動檢查並啟動
