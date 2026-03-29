---
name: supervision-command-permission-request
description: "監察組執行窗口：各組 agent 的所有受限操作（指令執行、檔案寫入、跨組 -p）均須送此審核，核可後由監察組代為執行。"
---

# Command Permission Request

## 核心設計

**任何 agent 不持有 `--allowedTools`。** 所有受限操作一律以 plain `claude -p` 送此處，由監察組評估後代為執行。

```
agent plain -p → command-permission-request → 評估 → 監察組帶工具執行
```

監察組的 `--allowedTools` 由 `call-agent`（通訊組）在呼叫時注入。bootstrapping 期間由人類扮演此角色。

## 目錄結構

```
command-permission-request/
├── .agent/
│   ├── rules/permission-policy.md      # 允許 / 拒絕判斷規則
│   └── workflows/evaluate-request.md   # 審核與執行流程
├── audit-log/                           # 稽核日誌（append-only，不入版控）
│   └── YYYYMMDD.jsonl
└── README.md
```

## 呼叫方式（各組統一介面）

```sh
cd /data/logos/supervision/command-permission-request && \
claude -p "Permission request:
from: <組別>
type: bash | write | cross-team-p
working_dir: <工作目錄>
request: <具體說明要做什麼>
original_prompt: <完整原始 prompt（cross-team-p 時含目標組路徑）>"
```

注意：**caller 不帶任何 `--allowedTools`**

## 三種請求類型

| type | 說明 | 監察組執行方式 |
|------|------|--------------|
| `bash` | 執行 terminal 指令 | 帶 `Bash` 執行指令 |
| `write` | 寫入 / 修改 / 刪除檔案 | 帶 `Write` 或 `Bash`(mv) 執行 |
| `cross-team-p` | 呼叫其他組別的 claude -p | 帶適當工具呼叫目標組 |

## 稽核日誌

`audit-log/YYYYMMDD.jsonl`，每行一筆：

```json
{
  "timestamp": "2026-03-29T14:00:00+00:00",
  "from": "education",
  "type": "write",
  "working_dir": "/data/logos/education/global-disciplines",
  "request": "新增 test-discipline.md",
  "decision": "approved",
  "reason": "組別寫入自身專案目錄"
}
```
