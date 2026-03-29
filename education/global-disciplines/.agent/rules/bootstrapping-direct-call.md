---
name: bootstrapping-direct-call
trigger: always_on
description: "說明 call-agent 尚未就位時的 bootstrapping 例外：人類暫代 call-agent 角色，負責注入 --allowedTools 給監察組。"
---

# Bootstrapping 期間的直接呼叫規範

## 前提

正常架構下，所有跨組呼叫都須經由 **call-agent**（通訊組）路由，由 call-agent 決定是否注入 `--allowedTools`。

**call-agent 尚未建制前**，此路由層不存在，需要人類暫代。

## Bootstrapping 例外

人類扮演 call-agent 的角色時，須遵守以下約束：

1. **只有呼叫監察組時才注入 `--allowedTools`**，其他組一律 plain `claude -p`。
2. 注入的工具以**最小必要**為原則（例如只需寫檔就給 `Write`，不要一律給 `Bash,Write`）。
3. 此例外僅適用於 call-agent 就位前的過渡期。

## 呼叫監察組範例（人類執行）

```sh
cd /data/logos/supervision/command-permission-request && \
claude --allowedTools "Bash,Write" -p "Permission request:
from: <請求組別>
type: bash | write | cross-team-p
working_dir: <路徑>
request: <說明>
original_prompt: <完整 prompt>"
```

## call-agent 就位後

將此規則視為過渡文件。call-agent 建制完成後，人類不再需要手動注入工具，改由 call-agent 統一處理路由與授權。
