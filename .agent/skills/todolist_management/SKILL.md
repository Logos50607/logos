---
name: todolist_management
description: 用於管理專案中的 TODOLIST.md，確保格式統一且包含日期紀錄。
---

# TODOLIST Management Skill

此 Skill 用於規範與自動化管理專案根目錄下的 `TODOLIST.md` 或 `todo_list.md` 檔案。

## 格式規範 (Format Rules)

1.  **條列式撰寫**: 所有項目必須以 Markdown 條列式 (List) 撰寫。
2.  **Checkbox**: 在每項條列標號前面，必須包含一個 Checkbox (`- [ ]` 或 `- [x]`)。
3.  **日期紀錄**: 在條列標號（或 Checkbox）之後、具體內容之前，必須加上該項目的**加入日期**，格式為 `YYYY-MM-DD`（例如：`2026-03-06`）。
4.  **內容分組**: （可選）可以根據「尚未裁斷的衝突」、「尚未完成項」、「未來優化」進行二級標題分組。

## 執行步驟

- 當需要更新 TODO 時，主動讀取此格式規範。
- 確保新加入的項目都帶有當前日期。
- 已完成的項目標註為 `[x]`。
