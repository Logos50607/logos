# Antigravity Skills 系統

本目錄存放了 Antigravity 全域適用的技能 (Skills)，用於擴展 AI
的特定任務處理能力。

## 目錄結構

- `rule_management/`: 用於維護與建立 Antigravity Rules。
- `skill_management/`: 用於維護與建立技能系統。
- `workflow_management/`: 用於維護與建立工作流 (Workflows)。
- `web_content_extraction/`: 包含擷取網頁內容並轉換為 Markdown
  的核心邏輯與腳本。

## 使用指引

1. **查閱 SKILL.md**: 每個技能資料夾內均有
   `SKILL.md`，定義了其功能、參數與使用方式。
2. **開發規範**: 技能內部的腳本應維持在 100 行以內，並優先採用模組化設計。
3. **元資料**: 所有的 `SKILL.md` 必須包含 YAML frontmatter 資料。
