---
name: supervision-permissions
description: "權限治理專案：審核各組 agent 的受限操作請求，自動判斷或轉人工，並以最小授權重執行原始任務。"
---

# 權限治理 (Permissions)

## 核心目標

當任何組別的 `claude -p` agent 在執行中遭遇受限操作（寫檔、執行指令等）被擋下時，提供統一的審核、記錄與重執行機制。

## 目錄結構

```
permissions/
├── .agent/
│   ├── rules/permission-policy.md     # 允許 / 拒絕的判斷規則
│   └── workflows/evaluate-request.md  # 審核流程
├── audit-log/                          # 稽核日誌（append-only）
│   └── YYYYMMDD.jsonl
└── README.md
```

## 呼叫方式（各組 escalation 介面）

當 agent 被擋下時，執行：

```sh
cd /data/logos/supervision/permissions && \
claude --allowedTools "Bash,Write" -p \
"Permission request:
from: <呼叫方組別>
working_dir: <原始工作目錄>
tool: <需要的 tool，如 Write / Bash>
action: <一行說明要做什麼>
original_prompt: <完整原始 prompt>"
```

## 審核結果

- **允許**：監察組以 `--allowedTools <tool>` 重執行原始 prompt，回傳結果
- **拒絕**：回傳拒絕原因，不重執行
- **轉人工**：寫入聯絡組待辦，等待使用者裁示

## 稽核日誌格式

`audit-log/YYYYMMDD.jsonl`，每行一筆：

```json
{
  "timestamp": "2026-03-29T14:00:00+00:00",
  "from": "education",
  "working_dir": "/data/logos/education/global-disciplines",
  "tool": "Write",
  "action": "新增 test-discipline.md",
  "decision": "approved",
  "reason": "符合 education 組寫入自身 .agent/ 的預設允許規則"
}
```
