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
  僅提取使用者要求的特定部分，忽略側邊欄、導覽列及廣告。
- **Markdown 轉換**: 使用 HTML 轉 Markdown 工具（優先選用純 `sh` 版本）。
- **清理內容**: 移除冗餘的樣式資訊、指令碼與隱藏元素，僅保留語義化的標籤。

## 3. 本地工具: `extract.sh`

本技能內建了一個純 `sh` 腳本，用於快速擷取並轉換 Markdown：

- **路徑**: `.agent/skills/web_content_extraction/scripts/extract.sh`
- **使用方式範例**:
  ```bash
  # 從 URL 讀取
  sh .agent/skills/web_content_extraction/scripts/extract.sh "https://example.com"
  # 從 檔案 讀取
  sh .agent/skills/web_content_extraction/scripts/extract.sh "file.html"
  # 從 STDIN 讀取
  cat index.html | sh .agent/skills/web_content_extraction/scripts/extract.sh
  ```
- **核心功能**:
  - 完全使用 `sed`, `awk`, `curl` 編寫，不依賴 Python/Node.js。
  - 自動移除 `script`, `style`, `nav` 等標籤。
  - 處理標題、列表、加粗、超連結及圖片標籤。
  - 處理常見 HTML 實體符號。

## 4. 品質保證與測試 (QA & Testing)

每個腳本開發後必須包含測試，並確實驗收。

- **測試腳本**: `.agent/skills/web_content_extraction/scripts/test_extract.sh`
- **執行測試**:
  ```bash
  sh .agent/skills/web_content_extraction/scripts/test_extract.sh
  ```

## 5. 依賴管理 (Dependencies)

所有腳本所需的外部依賴必須記錄於專案根目錄的
`DEPENDENCIES.md`。執行前請先確認環境：

- 核心依賴：`curl`, `sed`, `awk` (皆為 Linux 標準工具)。

## 6. Workflows 範例

建議搭配 `/fetch-web-content` 工作流使用：

1. 嘗試 `read_url_content` 或 `extract.sh`。
2. 若內容不完整，切換至 `browser_subagent`。
3. 擷取核心 HTML 並使用 `extract.sh` 將其轉為 Markdown。

## 7. 最佳實踐

- **節省 Token**: 確保轉換後的 Markdown 精簡且具語義。
- **台灣正體中文**: 輸出的摘要與說明應使用台灣正體中文。
