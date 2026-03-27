---
name: sync_disciplines_project
trigger: manual
description: "將當前專案的 .agent/ disciplines 同步至 .claude/，讓 Claude Code 可以吃到專案層級的 rules 與 workflows。"
---

# Skill: sync_disciplines_project

## 用途

此 skill 專為**專案層級**設計，與全域的 `sync_disciplines` skill 無關。
將專案自己的 `.agent/rules` 與 `.agent/workflows` 同步進 `.claude/`。

## 同步對應

| 來源 | 目標 | 策略 |
|------|------|------|
| `.agent/rules/` | `.claude/CLAUDE.md` | insert_text（marker 區塊注入）|
| `.agent/workflows/` | `.claude/commands` | soft_link |

## 執行方式

```bash
bash /home/logos/.gemini/.agent/skills/sync_disciplines_project/scripts/sync.sh [project_root]
```

- `project_root` 省略時自動使用 `git rev-parse --show-toplevel`。
- 由 `/sync-disciplines` workflow 呼叫，通常不需直接執行。
