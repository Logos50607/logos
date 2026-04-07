---
name: reporting
trigger: always_on
description: "訊息摘要呈報規則：定義呈報時機、呈報 channel 選擇，以及摘要的格式要求。"
---

# 呈報規則

## 呈報目標

呈報目標由 `.env` 的 `REPORT_CHANNEL` 與 `REPORT_TARGET_ID` 決定，**不得 hardcode**。

呈報前必須確認目標 channel 可用；不可用時記錄錯誤，不得靜默失敗。

## 呈報時機

### 定期呈報

依 `REPORT_SCHEDULE`（cron 格式）執行。每次定期呈報：
- 收錄自上次呈報以來所有 `normal` 以上優先級的訊息
- 以時間順序排列，`critical` / `high` 置頂
- 若無新訊息，**不發送**空白摘要

### 立即呈報

優先級達到 `REPORT_IMMEDIATE_PRIORITY` 時，不等下次定期時程，立即推送。

立即呈報只包含該則觸發訊息及其摘要，不附帶其他訊息。

### 不呈報的情況

- `low` 優先級訊息（除非手動觸發全量摘要）
- 掃描失敗的錯誤（除非連續 3 輪，升為 `critical`）
- 已在本輪立即呈報過的訊息，不得再出現在定期摘要中

## 摘要格式

```
【摘要】2026-04-07 08:00

🔴 緊急（1 則）
  [line-personal] 張三：「請你今天幫我確認一下合約」

🟡 待處理（2 則）
  [line-official] 李四：「這個功能什麼時候上線？」
  [line-personal] 群組A：「下週會議改時間」

⚪ 資訊（3 則）
  … （可摺疊）
```

- 每個區塊顯示則數，超過 5 則則摺疊，提供「查看全部」指示
- 發送者名稱匿名化選項由 `.env` 的 `REPORT_ANONYMIZE` 控制（預設 `false`）

## 呈報後處理

呈報成功後，將已呈報的訊息 ID 列表寫入狀態（避免重複呈報）。
狀態檔路徑由 `.env` 的 `STATE_PATH` 指定（預設 `./data/state.json`）。
