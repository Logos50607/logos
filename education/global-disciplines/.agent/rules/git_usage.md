---
name: git_usage
trigger: always_on
description: "Git 版控規範，定義了自動提交機制與訊息格式要求。"
---

# Git 提交規範 (Git Commit Convention)

本規則旨在確保專案歷史紀錄的整潔、清晰及具備語義。

## 1. 自動提交規範

- **即時提交**：在任何檔案變更（建立、修改、更名、刪除）後，AI **必須立即執行**
  `/git-commit` 工作流。
- **訊息格式**：Commit
  訊息應簡明地說明修改內容，並統一使用**台灣正體中文**。建議使用常見的前綴（例如
  `feat:`, `fix:`, `doc:`, `chore:`, `refactor:`）。

## 2. Amend 規範

- **略為修正直接 amend**：若變更屬於對上一次 commit 的微幅修正（如 typo、路徑修正、格式調整），應使用 `git commit --amend` 併入上一個 commit，而非產生新的 commit。
- **獨立變更則新增 commit**：若變更涉及新功能、不同檔案群組或與上一次 commit 無直接關聯，則應建立新的 commit。
