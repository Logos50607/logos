---
name: global_guidelines_index
description: "Antigravity 全域規則索引，定義了全域適用的規則、工作流與技能。"
---

# Antigravity 全域綱領 (Global Guidelines Index)

本文件作為全域規則 (rules)、技能 (skills)、與工作流 (workflows)
之索引，其細則列於 ~/.gemini/.agent 資料夾下。

## 0. 核心守則

- 每次在更動 ~/.gemini/.agent 下任何檔案時，都必須同步更新此文件。
- 本文件為 ~/.gemini/.agent 下所有檔案之表頭 yml 檔的集合。
- 載入所有 ~/.gemini/.agent/rules 中所有項目。
- 嚴禁將 ~/.gemini
  中任何檔案內容複製到個別專案中。規則應該直接遵循或參考，而非直接物理複製。

## 1. rules (規則)

- **language.md**: ALWAYS ON。確保使用台灣正體中文。
- **agent_behavior.md**: ALWAYS ON。規範重複指令限制、主動中斷與規則持續維護。
- **project_setup_files.md**: ALWAYS ON。定義專案結構、`.agent`
  目錄用途以及管理清單的管理規範。
- **gemini_md_management.md**: ALWAYS ON。規範專案層級 GEMINI.md 的初始化狀態與
  Metadata 索引要求。
- **readme_management.md**: ALWAYS ON。規範 README.md 的優先讀取原則與維護職責。
- **todolist_format.md**: 當編輯 `AGENT_PLAN.md` 或 `ASK_HUMAN.md`
  時遵循（Glob）。規範清單格式、日期與排序。
- **metadata_format.md**: 當編輯 `GEMINI.md` 或 `.agent/` 下所有檔案時遵循，定義
  YAML frontmatter 格式。
- **git_usage.md**: 執行 Git 版控操作時遵循。規範提交語義與歷史紀錄整理。
- **development_guidelines.md**:
  開發功能或重構時遵循。規範測試驅動、依賴管理與模組化結構。
- **web_content_extraction.md**: 擷取網頁內容的使用時機與規範。

## 2. 工作流 (Workflows)

- **[/setup-project]**: 初始化或檢查專案結構與管理清單。
- **[/fetch-web-content]**: 擷取指定網頁內容（URL 或檔案）並轉換為 Markdown。
- **[/git-commit]**: 執行標準化的 Git 提交流程，包含變更分析與總結。

## 3. 專屬技能 (Skills)

- **[skill_management]**: 用於建立、組織及維護技能系統。
- **[rule_management]**: 用於建立與維護 AI 行為規範及專案約束。
- **[workflow_management]**: 用於定義結構化的步驟、程序或斜線指令。
- **[web_content_extraction]**: 整合本地腳本與瀏覽器工具，高效擷取網頁內容。
