---
name: run-scheduled-task
description: "執行單一排程任務，依 command.type 分支處理，產出標準化執行報告。"
---

# 執行單一排程任務

## 用途

接收一個 task_name，從 registry 讀取任務定義，依 `command.type` 執行，產出 `EXECUTION_REPORT`。

## 輸入

- `task_name`：要執行的任務名稱
- `trigger`：`scheduled`（排程觸發）或 `manual`（手動觸發），預設 `scheduled`

## 執行步驟

### 1. 讀取任務定義

- 從 `registry/<task_name>.md` 讀取 manifest 內容。
- 若檔案不存在 → 產出 `status=skipped` 報告，附註「任務未註冊」，結束。
- 若 `enabled=false` → 產出 `status=skipped` 報告，附註「任務已停用」，結束。

### 2. 準備執行環境

- 切換工作目錄至 `command.working_dir`。
- 確認所需檔案存在：
  - `command.type=script`：確認 `script_path` 存在且可執行。
  - `command.type=ai-evaluate`：確認 `prompt_path` 存在；若有 `script_path` 亦確認。
- 產生 `execution_id`：格式 `YYYYMMDD-HHMMSS-<task_name>`。
- 記錄開始時間。

### 3. 執行任務

#### 分支 A：`command.type = script`

```sh
cd <working_dir>
bash <script_path> 2>&1
```

- 捕獲 stdout + stderr 合併輸出。
- 以 exit code 判斷：`0` = success，非 `0` = failure。
- 記錄執行耗時。

#### 分支 B：`command.type = ai-evaluate`

1. **前置資料蒐集**（若 `script_path` 有值）：
   ```sh
   cd <working_dir>
   bash <script_path> 2>&1 > /tmp/<execution_id>-data.txt
   ```

2. **組裝 prompt**：
   - 讀取 `prompt_path` 的內容。
   - 若有前置腳本輸出，附加至 prompt 末尾。
   - 若 manifest body 有補充說明，亦附加。

3. **AI 評估**：
   ```sh
   claude -p < <assembled_prompt>
   ```

4. **判斷結果**：
   - AI 輸出需包含明確的 status 結論（成功/失敗/部分完成）。
   - 若 AI 輸出無法判斷 → `status=failure`，附註「AI 評估結果不明確」。

### 4. 重試邏輯

當步驟 3 結果為 failure 時：

- 若 `attempt < retry.max_attempts`：
  - 等待 `retry.delay_seconds` 秒。
  - `attempt += 1`。
  - 回到步驟 3 重新執行。
- 若 `attempt >= retry.max_attempts`：
  - 維持 `status=failure`。
  - 進入步驟 6（失敗處理）。

### 5. 產出報告

依 `EXECUTION_REPORT` 範本填寫所有欄位：

- `task_name`, `execution_id`, `timestamp`, `status`, `duration_seconds`, `attempt`, `trigger`
- Body：執行摘要、輸出內容、異常紀錄（若有）

報告存放：
- 主要：`reports/YYYYMMDD/<task_name>.md`
- 若 manifest 指定 `report.destination`：同時複製至該路徑。

### 6. 失敗處理

若 `status=failure`（重試用盡）：

- 觸發 `/handle-failure` workflow，傳入 `task_name` 與報告路徑。

## 輸出

- 執行報告檔案路徑
- 執行狀態（供 daily-dispatch 彙整）
