---
name: escalate-to-supervision
trigger: model_decision
description: "當 agent 執行受限操作被擋下時，如何向監察組提出 permission request 並等待重執行。"
---

# 向監察組 Escalate 受限操作

## 觸發時機

當 `claude -p` 執行中遇到以下情況時使用：

- 嘗試寫檔、刪檔，收到「permission denied」或「write not allowed」
- 嘗試執行指令，被工具限制擋下
- 任何需要比當前 `--allowedTools` 更高權限的操作

## 呼叫方式

**caller 不帶任何 `--allowedTools`**，監察組的工具由 call-agent 在路由時注入；bootstrapping 期間由人類扮演此角色。

```sh
cd /data/logos/supervision/command-permission-request && \
claude -p "Permission request:
from: <你的組別名稱>
type: bash | write | cross-team-p
working_dir: <你原本的工作目錄>
request: <具體說明要做什麼>
original_prompt: <你原本被擋下的完整 prompt>"
```

## 等待結果

監察組會依 policy 回傳以下三種結果之一：

- **允許**：監察組已代為重執行，結果直接回傳
- **拒絕**：附上拒絕原因，不重執行
- **轉人工**：已記錄，等待使用者裁示後再處理

## 注意事項

- 不得繞過監察組直接重試受限操作
- `original_prompt` 必須完整，監察組依此重執行，不完整會導致結果不符預期
