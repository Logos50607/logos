---
id: education.extract-disciplines
target: education
cwd: /data/logos/education/knowledge-synthesis
provider: claude
mode: fire
risk: low
review: skip
description: "從指定 session 萃取可沉澱為 discipline 的模式，產出草稿存入 reports/discipline-proposals/。"
---

## Payload 格式

```
session: <~/.claude/projects/.../uuid.jsonl>
focus: <萃取重點，如「爬蟲技巧」>（可選）
```

## 目標組入口

目標組需有 `receive-task` workflow，接收上述 payload 並呼叫 `extract-disciplines` skill。

## 前置條件

- `education/knowledge-synthesis` 目錄已建立
- 教育組已有 `receive-task` workflow
