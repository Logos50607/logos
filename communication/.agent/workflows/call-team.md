---
name: call-team
description: "跨組任務呼叫的執行流程。任何組需要呼叫另一組時使用此 workflow。"
trigger: manual
---

# call-team 執行流程

## 輸入

```
task_id: <team>.<task-name>   # 必須已在 registry 登記
payload: <任務描述或資料>      # 傳給目標組的內容
```

## 步驟

### 1. 查詢 Registry

讀取 `registry/<team>/<task-name>.md`。
若不存在 → **拒絕執行**，回傳錯誤：「任務未登記，請先在通訊組 registry 建立對應條目。」

### 2. 決定是否送審

依 registry 的 `risk` 與 `review` 欄位：

- `review: skip` 或 `risk: low` → 跳至步驟 4
- `review: required` 或 `risk: medium/high` → 執行步驟 3

### 3. 送監察組審核

```bash
echo "<task_id>: <payload 摘要>" | claude -p "請審核此跨組任務是否符合規範" \
  --cwd /data/logos/supervision/...
```

等待監察組回應：
- 核可 → 繼續步驟 4
- 拒絕 → 終止，回傳監察組拒絕理由

### 4. 選擇 Provider

依 registry `provider` 欄位，若 quota 不足則 fallback（查詢內控組）。

### 5. 執行 -p 呼叫

```bash
echo "<payload>" | <provider> -p "請執行以下任務（task_id: <task_id>）" \
  --cwd <registry.cwd>
```

### 6. 回傳結果

- `mode: fire` → 不等待，直接結束
- `mode: reply` → 等待 stdout，回傳給發起組

## 前置條件

- 目標組已有 `receive-task` workflow（被 `-p` 喚醒的入口）
- 內控組已有 quota 查詢介面（`internal-control/quota-check`）
- 監察組已有跨組審核入口
