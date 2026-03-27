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
uv run capture.py --duration 60
```

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

## 模組狀態

| 功能 | 狀態 |
|------|------|
| 登入流程 | ✅ `run.py` |
| Inbound capture | ✅ `capture.py` |
| Outbound send | ⬜ 待建立 |
| Message processor | ✅ `src/processors/line_personal.py` |
