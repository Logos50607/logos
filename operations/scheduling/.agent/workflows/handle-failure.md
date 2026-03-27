---
name: handle-failure
description: "排程任務失敗後的處理流程：依 manifest 設定進行告警、降級與升級處理。"
---

# 失敗處理

## 用途

當 `run-scheduled-task` 執行結果為 `status=failure` 且重試用盡時，依 manifest 的 `failure` 設定進行告警、降級與升級處理。

## 輸入

- `task_name`：失敗的任務名稱
- `report_path`：對應的執行報告路徑

## 執行步驟

### 1. 讀取 manifest 設定

從 `registry/<task_name>.md` 讀取：
- `failure.notify`：告警方式
- `failure.fallback`：降級策略描述

### 2. 依 notify 設定分支處理

#### `notify = log`

- 更新 `registry/<task_name>.md` 的「最近失敗」區段，記入：
  - 失敗時間
  - 執行報告路徑
  - 錯誤摘要
- 更新 `registry/index.md` 中該任務的 `last_status` 為 `failure`。

#### `notify = escalate`

- 執行上述 `log` 的所有步驟。
- 寫入 `ASK_HUMAN.md`：
  ```
  - [ ] YYYY-MM-DD 排程任務 <task_name> 失敗，需人工介入。報告：<report_path>
  ```
- 若聯絡組回報機制就位：產出告警報告至聯絡組指定的收集路徑。
  - **前置條件**：聯絡組「回報統整」專案就位後啟用此步驟。目前僅寫入 ASK_HUMAN.md。

### 3. 降級處理

若 manifest 定義了 `failure.fallback`：

1. **AI 評估降級策略**：
   - 讀取 fallback 描述。
   - 結合執行報告的錯誤資訊。
   - 評估降級策略是否可安全執行。

2. **依評估結果分支**：
   - 可執行 → 執行降級操作，更新報告 `status=partial`，附註降級內容。
   - 不可執行 → 維持 `status=failure`，在報告中附註「降級策略不可行」及原因。

若未定義 fallback → 跳過此步驟。

### 4. 連續失敗檢查

讀取 `registry/<task_name>.md` 的歷史執行紀錄：

- 從 `reports/` 中收集該任務最近的執行報告。
- 若**連續 3 次以上** `status=failure`：
  - 自動將該任務的 `enabled` 設為 `false`。
  - 在 `registry/<task_name>.md` 標註停用原因：「連續失敗超過 3 次，自動停用」。
  - 寫入 `ASK_HUMAN.md`：
    ```
    - [ ] YYYY-MM-DD 排程任務 <task_name> 連續失敗 N 次，已自動停用。請決定是否調查根因或永久移除。
    ```

### 5. 提交變更

執行 `/git-commit`。

## 設計備註

- 降級處理由 AI 評估把關，避免自動執行可能造成更大問題的降級策略。
- 連續失敗自動停用是安全機制，防止持續浪費資源在無法成功的任務上。
- 所有升級處理最終都歸結到 `ASK_HUMAN.md`，確保人類有最終決策權。
