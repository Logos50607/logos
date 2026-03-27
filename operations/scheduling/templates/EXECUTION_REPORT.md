---
name: execution-report-template
description: "排程任務執行報告範本。每次任務執行後由 run-scheduled-task workflow 自動產出。"
---

# 執行報告範本

## 使用方式

此範本由 `run-scheduled-task` workflow 自動填寫產出，一般不需手動建立。
報告存放於 `reports/YYYYMMDD/<task_name>.md`。

## 報告格式

```yaml
---
# === 任務識別 ===
task_name: ""
# 對應 manifest 的 task_name

execution_id: ""
# 唯一執行編號，格式: YYYYMMDD-HHMMSS-<task_name>

# === 執行資訊 ===
timestamp: ""
# ISO 8601 執行時間（如 2026-03-26T09:00:00+08:00）

status: ""
# success: 執行成功
# failure: 執行失敗（含重試皆失敗）
# partial: 降級執行成功
# skipped: 任務已停用或條件不符，跳過執行

duration_seconds: 0
# 執行總耗時（含重試時間）

attempt: 1
# 第幾次嘗試（含重試）

trigger: ""
# scheduled: 排程觸發
# manual: 手動觸發
---
```

## Body 結構

```markdown
## 執行摘要

（一段話描述本次執行結果）

## 輸出

（腳本的 stdout/stderr 內容，或 AI 評估的結論）

## 異常紀錄

（僅 status=failure 或 status=partial 時填寫）

- **錯誤訊息**：
- **失敗步驟**：
- **已嘗試次數**：
- **建議後續處置**：
```

## 欄位說明

| 欄位 | 說明 |
|------|------|
| `task_name` | 與 manifest 對應，用於關聯查詢 |
| `execution_id` | 含時戳與任務名稱，便於排序與查找 |
| `timestamp` | 含時區的 ISO 8601 格式 |
| `status` | 四值枚舉，涵蓋所有執行結果 |
| `duration_seconds` | 含重試的總耗時，用於效能趨勢分析 |
| `attempt` | 用於追蹤重試情況 |
| `trigger` | 區分排程自動觸發與人工手動觸發 |

## 日報格式

`daily-dispatch` workflow 每日產出 `reports/YYYYMMDD/daily-summary.md`，格式如下：

```markdown
---
date: "YYYY-MM-DD"
total_tasks: 0
success: 0
failure: 0
partial: 0
skipped: 0
---

## 每日排程執行日報

| 任務 | 狀態 | 耗時 | 備註 |
|------|------|------|------|
| <task_name> | success | 12s | — |
| <task_name> | failure | 45s | 重試 3 次後仍失敗 |

## 異常任務摘要

（僅列出 failure / partial 任務的簡要說明）
```

此日報為聯絡組「回報統整」專案的輸入源。
