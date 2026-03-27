---
name: line-personal
description: "LINE 個人帳號 channel：CDP tap on LINE Chrome extension，read-only inbound，outbound 待建立。"
---

# LINE 個人帳號 Channel

## 運作原理

透過 Chrome DevTools Protocol（CDP）連接已登入 LINE extension 的 Chrome instance，
監聽 service worker 對 `line-chrome-gw.line-apps.com` 的 HTTP 流量，
**不開啟 LINE UI**，因此不觸發 `sendChatChecked`（訊息保持未讀）。

## 前置作業

### 1. 啟動 Chrome（含 LINE extension，開啟 CDP）

```bash
CHROME_DATA=$(bash $LOGOS_ROOT/internal-control/scripts/get-secret.sh \
  line-personal-session liaison/switchboard)

flatpak run com.google.Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$CHROME_DATA" \
  --profile-directory="Profile 1"
```

交付模式（無 monorepo）：
```bash
flatpak run com.google.Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$LINE_PERSONAL_SESSION" \
  --profile-directory="Profile 1"
```

### 2. 確認 LINE extension 已登入

Chrome 啟動後，開啟 LINE extension 並確認已登入。之後可關閉 LINE UI 視窗，
CDP 仍會持續監聽 service worker。

## 執行 capture

```bash
# 錄製 60 秒（預設）
uv run capture.py

# 自訂秒數與輸出路徑
uv run capture.py --duration 120 --output /tmp/line-capture.json
```

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LINE_PERSONAL_CDP_URL` | `http://localhost:9222` | Chrome CDP 端點 |
| `LINE_PERSONAL_EXT_ID` | `ophjlpahpchlmihnnnihgmmeilfjmjjc` | LINE extension ID |

## 模組狀態

| 功能 | 狀態 |
|------|------|
| Inbound capture | ✅ `capture.py` |
| Outbound send | ⬜ 待建立 |
| Message processor | ⬜ 待建立（見 `processors/`）|
