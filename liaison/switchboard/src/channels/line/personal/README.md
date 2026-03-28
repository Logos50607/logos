---
name: line-personal
description: "LINE 個人帳號 channel：CDP tap on LINE Chrome extension，read-only inbound，outbound 待建立。"
---

# LINE 個人帳號 Channel

## 核心目標

透過 Chrome DevTools Protocol（CDP）連接已登入 LINE extension 的 Chrome instance，
監聽 service worker 對 `line-chrome-gw.line-apps.com` 的 HTTP 流量，
**不開啟 LINE UI**，因此不觸發 `sendChatChecked`（訊息保持未讀）。

## 檔案結構

| 檔案 | 職責 |
|------|------|
| `run.py` | 登入主流程（骨幹，協調各模組） |
| `browser.py` | Chrome / Xvfb 安裝與啟動管理 |
| `extension.py` | LINE Chrome extension 下載、解壓、key 注入 |
| `qr.py` | QR code 擷取、顯示、登入狀態監聽 |
| `capture.py` | 攔截 service worker 訊息並錄製 |
| `diagnose.py` | 診斷工具（頁面狀態、網路攔截） |

## 登入流程

```
uv run run.py
```

內部步驟：
1. **確認 Chromium 已安裝**（`browser.ensure_installed`）
2. **確認 LINE extension 已下載並注入 key**（`extension.ensure_ready`）
3. **確認 Xvfb 與 Chrome 已啟動**（`browser.ensure_running`）
4. 連接 CDP，開啟 LINE extension panel
5. **顯示 QR code**（terminal ASCII + HTTP server）
6. 等使用者掃描後按 Enter
7. 輪詢登入狀態，偵測確認號碼（6 位數）或完成

### QR code 顯示方式

- **Terminal ASCII**：直接印在 terminal，可能因字型大小掃不到
- **HTTP 備用圖片**：`http://<ip>:8888/`，用手機瀏覽器開啟掃描（較可靠）

> 只能在 terminal 執行，無 GUI 介面。

## 抓資料

登入後執行：

```bash
# 抓 initial sync（reload extension，等 5 秒無流量後結束，存成 JSON）
uv run capture.py fetch

# 抓特定日期之後的資料
uv run capture.py fetch --since 2025-01-01

# 持續監聽新訊息（每筆即時 append 到 JSONL）
uv run capture.py listen

# 印到 stdout（測試用）
uv run capture.py watch
```

### capture 模式說明

| 模式 | 說明 | 輸出 |
|------|------|------|
| `fetch` | reload extension 觸發 initial sync，5 秒無流量後結束 | `captured.json` |
| `listen` | 持續監聽，每筆即時 append | `captured.jsonl` |
| `watch` | 同 listen，但印到 stdout | stdout |

> `fetch` 模式抓到的是 LINE extension 啟動時的 initial sync，約 40+ 筆 API，含聊天室清單、聯絡人、訊息盒子等。

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LINE_PERSONAL_CDP_URL` | `http://localhost:9222` | Chrome CDP 端點 |
| `LINE_PERSONAL_CDP_PORT` | `9222` | Chrome CDP port |
| `LINE_PERSONAL_DISPLAY` | `:99` | Xvfb display |
| `LINE_PERSONAL_SESSION` | （由 get-secret.sh 取得）| Chrome user-data-dir 路徑 |
| `LINE_PERSONAL_EXT_ID` | `ophjlpahpchlmihnnnihgmmeilfjmjjc` | LINE extension ID |

## 技術細節

### CRX3 key 注入

LINE extension 以 unpacked 方式載入時會得到隨機 ID，
LINE server 會拒絕（`ltsm_not_available`）。
`extension.py` 從 CRX3 protobuf header 提取 public key，
注入 `manifest.json` 的 `key` 欄位，確保 Chrome 計算出正確的 store ID。

### QR decode

LINE canvas QR 尺寸 115×115px，以 `zxing-cpp` 放大 5x 解碼，
取得完整 URL（含 `secret` 參數）後重新生成大圖供手機掃描。

## 抓完整訊息歷史

登入並執行 `capture.py fetch` 後，可再呼叫：

```bash
# 抓所有聊天室（預設每室 50 則）
uv run fetch_messages.py

# 每室抓 200 則
uv run fetch_messages.py --count 200

# 只抓指定聊天室
uv run fetch_messages.py --chat CF8at21O... --count 100

# 指定輸出路徑
uv run fetch_messages.py --output /tmp/msgs.json
```

輸出為 `messages.json`，格式：`{messageBoxId: [message, ...]}`。

### 運作原理

1. 透過 CDP 連接既有 Chrome，找到 LINE extension page
2. reload page 並攔截請求取得 `X-Line-Access` token
3. 每次 API 呼叫前，透過 `ltsmSandbox` iframe postMessage 計算 `X-Hmac`
4. 以 Python `urllib` 直接呼叫 LINE GW API（`getRecentMessagesV2` + `getPreviousMessagesV2WithRequest`）
5. 從 `captured.json` 的 `getMessageBoxes` 取得所有 messageBoxId 清單

## 模組狀態

## 發送訊息

```bash
uv run send_message.py --to <mid> --text "訊息內容"
```

### 運作原理

1. 連接 CDP 找到 extension page
2. 導航到 `#/chats/<mid>`，點擊聊天室項目
3. 在 `chatroomEditor` contenteditable div 輸入文字，按 Enter
4. Extension 自動觸發 `negotiateE2EEPublicKey` → `sendMessage`（E2EE 加密）
5. 確認 `sendMessage` request 觸發後返回原始頁面

> 注意：發送會觸發 `sendChatChecked`，目標聊天室訊息標為已讀。

## 模組狀態

| 功能 | 狀態 |
|------|------|
| 登入流程 | ✅ `run.py` |
| Inbound capture | ✅ `capture.py` |
| Fetch 完整訊息 | ✅ `fetch_messages.py` |
| Outbound send | ✅ `send_message.py` |
| Message processor | ✅ `src/processors/line_personal.py` |
