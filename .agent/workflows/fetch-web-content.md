---
description: 擷取指定網頁內容並轉換為 Markdown
---

# /fetch-web-content 工作流

本工作流旨在將指定 URL 的網頁內容擷取、轉換並呈現為 AI 易於理解的 Markdown
格式。

## 執行步驟

1. **嘗試快速擷取**:
   - 優先調用 `.agent/skills/web_content_extraction/scripts/extract.sh`
     工具抓取內容。
   - `sh .agent/skills/web_content_extraction/scripts/extract.sh <URL>`

2. **驗證內容品質**:
   - 如果 `extract.sh` 返回結果為空，或內容明顯包含 "Enable JavaScript"、"Wait a
     moment" 等字樣，則表示為動態網頁。

3. **後備方案 (動態網頁)**: // turbo
   - 使用 `browser_subagent` 工具在後台 (Headless) 開啟網頁。
   - 執行 `read_browser_page` 讀取完整 DOM。
   - 將讀取到的 HTML 透過管道傳給 `extract.sh` 進行 Markdown 轉換：
     `cat browser_page.html | sh .agent/skills/web_content_extraction/scripts/extract.sh`

4. **呈現結果**:
   - 將最終轉換出的 Markdown 內容呈現給使用者。
   - 若內容過長，請進行適度摘要或僅提供核心部分。
