---
name: scheduling-principles
trigger: always_on
description: "排程系統核心原則，規範聲明式註冊、config-driven 執行與標準化回報。"
---

# 排程系統核心原則

## 1. 聲明式註冊

- 任務的定義權在來源專案，營運組只負責收集與執行。
- 來源專案在自身 `.agent/schedules/` 放置 manifest 檔案，營運組定期掃描。
- 營運組不得修改來源專案的 manifest，僅讀取。
- 新增任務 = 來源專案新增一個 manifest 檔案，不需改動營運組程式碼或設定。
- 若 manifest 格式不合規，記入 `registry/invalid.md`，不自動修正。

## 2. Config-Driven

- 所有排程參數（頻率、重試、告警方式）從 manifest 的 YAML frontmatter 讀取。
- 禁止在 workflow 或腳本中硬編碼任何任務特定的參數。
- 排程邏輯對具體任務名稱無感知，以動態迭代方式處理所有已註冊任務。

## 3. 抽象與實作分離

- workflow 與 skill 層只描述「做什麼」與「判斷邏輯」。
- 底層實作機制（cron / systemd timer / 手動觸發）由 scripts/ 處理。
- 切換底層機制時，workflow 與 skill 不需修改。
- 測試方式：將底層從 cron 換成手動觸發，workflow 流程是否仍成立？若否，耦合過深。

## 4. 標準化回報

- 每次任務執行（無論成敗）必須產出符合 `EXECUTION_REPORT` 範本的報告。
- 報告同時存入營運組 `reports/YYYYMMDD/` 與來源專案指定的 `report.destination`。
- 每日產出 `daily-summary.md` 作為聯絡組「回報統整」專案的輸入源。

## 5. 失敗不靜默

- 任何 `status=failure` 必須觸發 manifest 中定義的 `failure.notify` 機制。
- `notify=log` 時至少記入報告與 registry 的最近失敗區段。
- `notify=escalate` 時額外寫入 `ASK_HUMAN.md` 請示人工介入。
- 重試次數用盡仍失敗時，無論 notify 設定為何，皆升級處理。
- 連續 3 次以上失敗的任務自動停用（`enabled=false`），並請示是否調查根因。
