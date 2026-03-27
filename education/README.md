---
name: education
description: "教育組：規範制定、技能培訓、互動觀察與知識管理。"
---

# 教育組 (Education)

## 核心目標

維護 AI 團隊的知識基礎：

1. 制定並同步 global disciplines（規則、技能、工作流）至所有 agent
2. 管理外部技能的吸納與引入流程
3. 觀察與記錄人機互動模式，持續優化 AI 行為規範

## 專案

| 專案 | 說明 |
|------|------|
| `global-disciplines/` | 所有 agent 共用的 rules/skills/workflows SSOT，透過 sync 機制分發 |
| `skill-adoption/` | 外部技能吸納策略框架與執行追蹤 |

## 關鍵機制

### Global Disciplines Sync

```
global-disciplines/.agent/rules/    ──→ insert_text ──→ ~/.gemini/GEMINI.md
                                    ──→ insert_text ──→ ~/.claude/CLAUDE.md
global-disciplines/.agent/workflows ──→ soft_link   ──→ ~/.claude/commands
                                    ──→ soft_link   ──→ ~/.gemini/antigravity/global_workflows
```

執行：`bash ~/.gemini/.agent/skills/sync_disciplines/scripts/sync.sh <agent>`
