---
name: scheduling-disciplines-index
description: "營運組排程基礎建設專案的 disciplines 索引。"
---

# Disciplines 索引

## Rules

| 名稱 | 檔案 | 說明 |
|------|------|------|
| scheduling-principles | `rules/scheduling-principles.md` | 排程系統核心原則：聲明式註冊、config-driven、標準化回報 |
| execution-boundary | `rules/execution-boundary.md` | 腳本層與評估層的分界定義與禁止行為 |

## Workflows

| 名稱 | 檔案 | 說明 |
|------|------|------|
| collect-manifests | `workflows/collect-manifests.md` | 掃描收集各專案的排程 manifest，更新 registry |
| run-scheduled-task | `workflows/run-scheduled-task.md` | 執行單一排程任務（script / ai-evaluate），產出報告 |
| daily-dispatch | `workflows/daily-dispatch.md` | 每日調度主流程：收集 → 比對 → 執行 → 日報 |
| handle-failure | `workflows/handle-failure.md` | 失敗處理：告警、降級、連續失敗自動停用 |

## Skills

| 名稱 | 檔案 | 說明 |
|------|------|------|
| schedule-health-check | `skills/schedule-health-check.md` | 排程系統健康檢查，識別異常與瓶頸 |
| execution-report-review | `skills/execution-report-review.md` | 執行報告趨勢分析，萃取異常與建議 |

## Templates

| 名稱 | 檔案 | 說明 |
|------|------|------|
| SCHEDULE_MANIFEST | `../templates/SCHEDULE_MANIFEST.md` | 排程註冊 manifest 範本 |
| EXECUTION_REPORT | `../templates/EXECUTION_REPORT.md` | 執行結果報告範本 |
