---
name: sync_disciplines
trigger: manual
description: "將 .agent/ 中的 global disciplines 同步至各 agent 的目標位置（antigravity、claude 等）。"
---

# Skill: sync_disciplines

## 用途

根據 `discipline_config.json` 的設定，將 `.agent/rules`、`.agent/workflows`、`.agent/skills`
同步至對應 agent 的目標路徑。

## 執行方式

```bash
bash /home/logos/.gemini/.agent/skills/sync_disciplines/scripts/sync.sh <agent_name>
```

| agent | 說明 |
|-------|------|
| `antigravity` | 同步至 Gemini CLI 工作目錄 |
| `claude` | 同步至 `~/.claude/`（全域 Claude Code）|

## 測試

```bash
bash /home/logos/.gemini/.agent/skills/sync_disciplines/scripts/test_sync.sh
```
