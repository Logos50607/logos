---
name: scraping_methodology
trigger: always_on
description: "爬蟲開發方法論：監聽技巧、認證機制、reCAPTCHA 限制，以及何時保留瀏覽器自動化。"
---

# 爬蟲開發方法論 (Scraping Methodology)

## 核心原則

爬蟲開發分為兩個階段，**不得在探索階段就定案**：

1. **探索階段**：允許使用瀏覽器自動化工具操作介面，以理解網站行為與資料流。
2. **定案階段**：探索完成後，**必須**監聽網路請求，找出背後的 HTTP API，改以純 API 呼叫實作最終方案。

## 為何要轉換

- 瀏覽器自動化速度慢、資源佔用高、容易因 UI 變動而損壞。
- 直接呼叫 API 更穩定、更快、更容易維護與測試。

## 實作順序

```
瀏覽器自動化探索 → 監聽網路請求找出 API endpoint
→ 確認 headers / payload / 認證機制
→ 改寫為純 API 腳本 → 移除瀏覽器自動化依賴
```

## 監聽技巧（Playwright）

### 必須同時監聽 request 與 response

只監聽 request 拿不到 API response 格式（如 channelId 欄位名稱）。**永遠都要同時掛兩個 handler**：

```python
ctx.on("request",  on_request)   # 看 method / url / body / headers
ctx.on("response", on_response)  # 看 status / response body / 取得 ID
```

### 監聽 context 而非 page

```python
# ❌ 只監聽當前分頁（錯過新開的分頁）
page.on("request", handler)

# ✅ 監聽整個 context（含所有分頁）
ctx.on("request", handler)
```

### 即時寫入日誌

不要等 Enter 才存檔。每次攔截到就立刻寫入：

```python
def on_request(req):
    _LOG.append(entry)
    _OUT.write_text(json.dumps(_LOG, indent=2, ensure_ascii=False))  # 即時
```

### Header 過濾要夠寬

過濾太嚴會漏掉關鍵 header（如 `x-xsrf-token`）。建議全部捕捉：

```python
"headers": dict(req.headers)  # 全抓，不過濾
```

### 擴大 host 過濾範圍

同一服務可能跨多個子網域（如 `entry.line.biz`、`manager.line.biz`、`developers.line.biz`）：

```python
HOSTS = ("line.biz", "line.me")  # 用上層網域覆蓋所有子網域
if not any(h in host for h in HOSTS):
    return
```

## 認證機制（Session-based SPA）

現代 SPA 通常使用 session cookie + XSRF-TOKEN，不是 Bearer token：

- **Session cookie**：通常是 `ses`，設在 `.parent-domain.com`（含所有子網域）
- **XSRF-TOKEN**：每個子網域可能有自己獨立的 token，需要先造訪目標網域後再取出

```python
# 先造訪目標網域讓瀏覽器建立 session
await page.goto("https://target.example.com/")
# 再取出該網域的 XSRF-TOKEN
cookies = await ctx.cookies(["https://target.example.com"])
xsrf = next((c["value"] for c in cookies if c["name"] == "XSRF-TOKEN"), "")
```

- **Playwright APIRequestContext**（`ctx.request.fetch`）比 urllib 更可靠，會自動帶 cookies

## Bot 偵測與 reCAPTCHA

### reCAPTCHA 無法在 headless 環境下通過

- reCAPTCHA v2 invisible 與 v3 都能偵測 headless/Xvfb 環境，包括 playwright-stealth 仍無效
- 只有**真實有頭瀏覽器**（`headless=False` + 真實 DISPLAY，如 `ssh -X`）才能通過

### 分離受 reCAPTCHA 保護的步驟

遇到 reCAPTCHA 時，正確做法是**拆分流程**，而不是嘗試繞過：

```
# 受 reCAPTCHA 保護的步驟 → 手動或 --headed 模式
# 其他 API 步驟 → 純 API 呼叫（headless）
```

提供 `--oa-id <id>` 等參數讓使用者跳過需要 reCAPTCHA 的建立步驟，直接進行後續設定。

### Headless 偵測

瀏覽器指紋（`sec-ch-ua` 含 `HeadlessChrome`、`navigator.webdriver = true`）可被伺服器識別。部分站台只對 GET 放行 headless，POST 仍拒絕。

## 例外情況

僅在純 API 技術上無法達成目標時（如 reCAPTCHA 保護），才允許保留瀏覽器自動化作為最終方案。
例外情況**必須在 README 或 `ASK_HUMAN.md` 中說明理由**，否則視為規範違反。
