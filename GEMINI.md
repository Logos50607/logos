# Antigravity 全域規則規範 (Global Guidelines Index)

本專案遵循 Antigravity 結構化開發模式，具體規範已分散至 `.agent` 目錄下：

## 1. 核心開發規範 (Rules)

- **[語言規範]** (`.agent/rules/language.md`): 統一使用台灣正體中文。
- **[工作區初始化]** (`.agent/rules/workspace_setup.md`):
  工作區目錄、TODOLIST、ASKHUMAN 與 README 規則。
- **[Git 提交規範]** (`.agent/rules/git_usage.md`): 自動提交、訊息格式與 Squash
  規範。
- **[行為與維護]** (`.agent/rules/agent_behavior.md`):
  重複指令限制、主動中斷與規則持續維護。
- **[開發品質]** (`.agent/rules/development_guidelines.md`):
  必須包含測試且記錄依賴於 `DEPENDENCIES.md`。

## 2. 工作流 (Workflows)

- **[/setup-workspace]**: 初始化或檢查工作區結構。
- **[/fetch-web-content]**: 擷取指定網頁內容並轉換為 Markdown。

## 3. 專屬技能 (Skills)

- **[skill_management]**: 管理與建立技能。
- **[rule_management]**: 管理與建立規則。
- **[workflow_management]**: 管理與建立工作流。
- **[web_content_extraction]**: 網頁內容擷取與 Markdown 轉換。
- **[todolist_management]**: TODOLIST 紀錄與排序規範。
