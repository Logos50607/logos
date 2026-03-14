---
name: web_content_extraction
trigger: manual
description: "定義何時應使用 /fetch_web_content 工作流來獲取網頁內容。"
---

# 網頁內容擷取規範 (Web Content Extraction Guidelines)

當需要獲取外部資訊時，應遵循以下使用時機與規範：

## 1. 使用時機

- **調研與參考**：當使用者提供 URL 並要求分析、總結或參考該網頁內容時。
- **自動化補全**：當需要特定文檔或網頁數據來輔助程式碼撰寫，且已知該數據存在於特定
  URL 時。
- **禁止行為**：嚴禁在未經使用者許可的情況下，頻繁或大規模爬取無關網頁。

## 2. 執行流程

- 始終優先執行 `/fetch_web_content` 工作流。
- 確保擷取的內容經過 Markdown 轉換，以節省 Token 並提高 AI 閱讀效率。
