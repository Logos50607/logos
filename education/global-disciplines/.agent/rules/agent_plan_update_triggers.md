---
name: agent_plan_update_triggers
trigger: always_on
description: "規範 AGENT_PLAN.md 何時必須更新，確保設計決策與完成進度即時反映。"
---

# AGENT_PLAN 更新觸發規範

## 取得當前 Session 路徑

任何需要標注來源的更新，先執行以下指令取得當前 session 路徑：

```bash
project_dir=$(pwd | tr '/' '-' | sed 's/^-//')
latest_session=$(ls -t ~/.claude/projects/${project_dir}/*.jsonl 2>/dev/null | head -1)
echo "session: $latest_session"
```

跨多個 session 時，列出範圍：

```bash
ls -t ~/.claude/projects/${project_dir}/*.jsonl
# 從輸出中取 uuid，oldest → newest
```

## 必須更新的時機

### 1. 設計方向改變
當對話中確立了新的設計方向（推翻或修正既有做法），必須：
- 在 AGENT_PLAN.md 新增或更正對應項目
- 加註來源 session

格式：
```
- [ ] <YYYY-MM-DD> <描述>
      （session: <latest_session 輸出值>）
```

跨多個 session：
```
- [ ] <YYYY-MM-DD> <描述>
      （sessions: <uuid-oldest> → <uuid-newest>, project: <project_dir>）
```

### 2. 任務完成
將項目標記 `[x]` 時，必須補上執行細節與驗證方式：

```
- [x] <YYYY-MM-DD> <描述>
      執行：<實際做了什麼>
      驗證：<如何確認已生效>
      session: <latest_session 輸出值>
```

## 格式

遵循 `todolist_format.md`：條列表、最新日期優先、日期格式 `YYYY-MM-DD`。
