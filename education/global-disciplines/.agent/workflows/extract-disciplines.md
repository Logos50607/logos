---
name: extract-disciplines
trigger: manual
description: "教育組定期或按需從各組對話摘要中萃取可沉澱為 global 或組內 discipline 的模式，產出草稿供人工審核。"
---

# 對話萃取 Discipline 工作流

## 觸發時機

- 每日排程自動執行（透過 `education-global-disciplines-extract` manifest）
- 或使用者主動要求時執行

## 執行步驟

1. **讀取 session 摘要**：執行 `scripts/collect-sessions.sh`，取得 `~/.claude/projects/` 中上次掃描後的新 session 內容摘要
2. **模式識別**：依以下條件篩選值得沉澱的內容：
   - **重複模式**：相同做法或約定在多個 session 中出現
   - **明確決策**：使用者確立了設計方向或規範
   - **錯誤更正**：AI 預設行為被使用者糾正，且具備通用性
   - **流程確立**：某工作流程被使用者認可為標準做法
3. **判斷層級**：global（所有組適用）或 project（特定組）
4. **產出草稿**：每個候選項輸出含 frontmatter 的完整 markdown 草稿，格式達到可直接放入 `.agent/rules/` 或 `.agent/workflows/` 的顆粒度
5. **標注待確認**：若設計仍不完整或有前置依賴，於草稿中明確標注

## 草稿輸出格式

```
### [discipline 名稱]

**類型**：rule / skill / workflow
**層級**：global 或 project（指定組別）
**觸發條件**：always_on / model_decision / glob / manual
**來源 session**：~/.claude/projects/<project-dir>/<uuid>.jsonl

**草稿內容**：
（含 frontmatter 的完整 markdown）
```

## 不產出的情況

- session 內容過於情境特定，無法通用化
- 設計仍在討論中，尚未有明確決策
- 本週期無符合條件的模式 → 輸出「本週期無新 discipline 建議」

## 草稿審核流程

產出的草稿存放於 `reports/discipline-proposals/`，需經以下步驟才正式生效：

1. 使用者或教育組 agent 確認草稿內容
2. 若屬 global → 寫入 `~/.gemini/.agent/rules/`，執行 sync
3. 若屬特定組 → 寫入該組的 `.agent/rules/` 或 `.agent/workflows/`
