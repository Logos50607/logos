---
name: web_content_extraction
description: "用於有效率地獲取網頁內容並轉換為 AI 友善的 Markdown 格式。當使用者要求查看網頁內容（而非除錯）時使用。"
---

# 網頁內容擷取與轉換指南 (Web Content Extraction)

本技能旨在指導 AI 如何以最節省資源且易於閱讀的方式獲取網頁內容，並將其轉換為
Markdown 格式供後續分析。

## 1. 擷取策略 (Execution Strategy)

為了平衡效率與完整性，應遵循以下優先順序：

1. **優先使用 `read_url_content`**:
   - 這是最快的方法，會直接嘗試獲取內容並自動轉換為 Markdown。
   - 適用於靜態網頁。

2. **若 `read_url_content` 失敗或內容不完整 (例如：JavaScript 動態載入)**:
   - 使用 `browser_subagent`。
   - **優先使用無頭模式 (Headless)**:
     除非需要使用者手動操作或登入，否則應在後台執行。
   - 使用 `read_browser_page` 讀取內容。

## 2. 轉換與過濾 (Extraction & Conversion)

獲取內容後，應進行處理以利 AI 閱讀：

- **局部擷取 (Relevant Slicing)**:
  僅提取使用者要求的特定部分（例如：文章主體、特定表格、API
  文件），忽略側邊欄、導覽列及廣告。
- **Markdown 轉換**: 使用 HTML 轉 Markdown 套件（如 `turndown`）或 AI 自行根據
  DOM 結構重新組織。
- **清理內容**:
  移除冗餘的樣式資訊、指令碼與隱藏元素，僅保留語義化的標籤（標題、清單、表格、連結）。

## 3. 推薦工具與庫

如果您有權限在本地環境執行腳本處理大量資料：

- **Turndown**: JavaScript 編寫的開源 HTML to Markdown 轉換器。
- **Node-html-markdown**: 專為 Node.js 最佳化的轉換庫。
- **@aiquants/html-to-markdown**: 專為 AI Agent 設計，支援動態內容抓取。

## 4. Workflows 範例

建議搭配 `/fetch-web-content` 工作流使用：

1. 嘗試 `curl` 或 `read_url_content`。
2. 若內容包含 "Enable JavaScript" 字樣，切換至 `browser_subagent`。
3. 擷取 `main` 或 `article` 標籤內的 HTML。
4. 格式化為 Markdown 並呈現給使用者。

## 5. 最佳實踐

- **隱私與安全**: 避免在未經使用者許可下進入需要登入的私人頁面。
- **節省 Token**: 轉換後的 Markdown 應保持精簡，避免傳送過多無關的 token 給 AI
  模型。
- **台灣正體中文**: 輸出的摘要與說明應使用台灣正體中文。
