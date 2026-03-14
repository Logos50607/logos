---
name: git_usage
trigger: always_on
description: "Git 版控規範，定義了提交訊息格式與歷史紀錄整理的要求。"
---

# Git 提交規範 (Git Commit Convention)

本規則旨在確保專案歷史紀錄的整潔、清晰及具備語義。

## 1. 自動提交與總結

- **主動提交**：在任何檔案變更（建立、修改、更名、刪除）後，AI **必須立即執行**
  `git commit`。
- **提交前置作業**：執行 commit 前先執行 `git diff`，歸納本次修改的實質要點。
- **訊息格式**：Commit 訊息應簡明地說明修改內容，並統一使用**台灣正體中文**。

## 2. 歷史紀錄整理

- **合併建議 (Squash)**：定期檢查近期提交紀錄。若發現多個 commit
  屬於同一邏輯變更，應主動請示使用者執行 `squash` 操作，以保持歷史紀錄整潔。
- **Commit Type**：建議使用常見的前綴（例如 `feat:`, `fix:`, `doc:`, `chore:`,
  `refactor:`）。
