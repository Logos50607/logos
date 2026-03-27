---
name: daily-dispatch
description: "每日排程調度主流程：更新 registry、篩選今日待執行任務、依序觸發、產出日報。"
---

# 每日排程調度

## 用途

作為排程系統的每日入口點，決定哪些任務該觸發，依序執行並產出日報。

## 建議觸發方式

- 每日固定時間由 cron 或 systemd timer 觸發
- 或由人工手動執行

## 執行步驟

### 1. 更新 registry

執行 `/collect-manifests` workflow，確保 registry 反映最新的 manifest 狀態。

### 2. 讀取任務清單

從 `registry/index.md` 讀取所有 `enabled=true` 的任務。

### 3. 排程比對

對每個任務，依據 `schedule.type` 判斷是否應於今日執行：

#### `type = cron`

- 解析 cron 表達式。
- 判斷當前時間是否符合表達式。
- 符合 → 加入待執行清單。

#### `type = interval`

- 從 `registry/<task_name>.md` 讀取最近一次執行時間。
- 計算距今間隔是否 ≥ `schedule.expr` 指定的時長。
- 若從未執行過 → 視為到期，加入待執行清單。
- 間隔到期 → 加入待執行清單。

#### `type = one-time`

- 判斷 `schedule.expr`（ISO 日期）是否為今日。
- 確認該任務尚未執行（reports/ 中無對應報告）。
- 兩者皆滿足 → 加入待執行清單。

### 4. 依序執行

對待執行清單中的每個任務：

- 呼叫 `/run-scheduled-task` workflow，傳入 `task_name` 與 `trigger=scheduled`。
- 收集回傳的執行狀態。
- **任務間獨立**：單一任務失敗不影響其他任務的執行。

### 5. 產出日報

彙整今日所有任務的執行結果，產出 `reports/YYYYMMDD/daily-summary.md`：

```yaml
---
date: "YYYY-MM-DD"
total_tasks: <數字>
success: <數字>
failure: <數字>
partial: <數字>
skipped: <數字>
---
```

Body 包含：
- 各任務一行摘要的狀態表
- 異常任務摘要（僅 failure / partial）

此日報為聯絡組「回報統整」專案的標準化輸入源。

### 6. 提交變更

執行 `/git-commit`。

## 無任務時的行為

若今日無任何待執行任務，仍產出日報（`total_tasks=0`），確保聯絡組可確認排程系統正常運作。
