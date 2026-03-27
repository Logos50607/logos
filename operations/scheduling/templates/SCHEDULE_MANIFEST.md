---
name: schedule-manifest-template
description: "排程註冊 manifest 範本。其他專案複製此檔至自身 .agent/schedules/<task_name>.manifest.md，填寫 frontmatter 以聲明排程需求。"
---

# 排程註冊 Manifest 範本

## 使用方式

1. 複製本檔至你的專案的 `.agent/schedules/` 目錄下
2. 將檔名改為 `<task_name>.manifest.md`（task_name 格式：`<group>-<project>-<task>`）
3. 填寫下方 YAML frontmatter 中的各欄位
4. 營運組的 `collect-manifests` workflow 會自動掃描並收集

## Manifest 格式

```yaml
---
# === 基本資訊 ===
task_name: ""
# 唯一識別名稱，格式: <group>-<project>-<task>
# 範例: education-skill-adoption-maintain-vendor

description: ""
# 任務描述，說明此排程做什麼、為什麼需要

owner_group: ""
# 歸屬組別（strategy / intelligence / education / liaison / operations / supervision / creation / internal-control / infrastructure / communication / delivery）

owner_project: ""
# 歸屬專案名稱

# === 排程設定 ===
schedule:
  type: ""
  # cron: 使用 cron 表達式（如 "0 9 * * 1" = 每週一 09:00）
  # interval: 使用間隔描述（如 "7d" = 每 7 天、"4h" = 每 4 小時）
  # one-time: 使用 ISO 日期（如 "2026-04-01"）
  expr: ""

# === 執行命令 ===
command:
  type: ""
  # script: 執行 shell 腳本（機械操作，以 exit code 判斷成敗）
  # ai-evaluate: 先蒐集資料，再由 AI 評估判斷

  script_path: ""
  # 腳本路徑（相對於專案根目錄）
  # type=script 時為必填
  # type=ai-evaluate 時為選填（作為資料蒐集前置腳本）

  prompt_path: ""
  # AI 評估用 prompt 檔案路徑（相對於專案根目錄）
  # 僅 type=ai-evaluate 時必填

  working_dir: ""
  # 執行時的工作目錄（絕對路徑）

# === 重試策略 ===
retry:
  max_attempts: 1
  # 最大嘗試次數（含首次執行）。1 = 不重試
  delay_seconds: 60
  # 重試間隔秒數

# === 失敗處理 ===
failure:
  notify: "log"
  # log: 僅記錄至報告
  # escalate: 記錄 + 寫入 ASK_HUMAN + 告警聯絡組

  fallback: ""
  # 降級策略描述（可選）。由 AI 評估是否可執行

# === 報告設定 ===
report:
  format: "markdown"
  # markdown 或 json

  destination: ""
  # 報告輸出路徑（相對於專案目錄）。留空則僅存入營運組 reports/

# === 啟用狀態 ===
enabled: true
---
```

## 欄位說明

| 欄位 | 必填 | 說明 |
|------|------|------|
| `task_name` | 是 | 全域唯一，格式 `<group>-<project>-<task>` |
| `description` | 是 | 任務描述 |
| `owner_group` | 是 | 歸屬組別 |
| `owner_project` | 是 | 歸屬專案 |
| `schedule.type` | 是 | `cron` / `interval` / `one-time` |
| `schedule.expr` | 是 | 對應 type 的表達式 |
| `command.type` | 是 | `script` / `ai-evaluate` |
| `command.script_path` | 條件 | script 類型必填，ai-evaluate 選填 |
| `command.prompt_path` | 條件 | ai-evaluate 類型必填 |
| `command.working_dir` | 是 | 執行時工作目錄 |
| `retry.max_attempts` | 否 | 預設 1 |
| `retry.delay_seconds` | 否 | 預設 60 |
| `failure.notify` | 否 | 預設 `log` |
| `failure.fallback` | 否 | 降級策略 |
| `report.format` | 否 | 預設 `markdown` |
| `report.destination` | 否 | 留空僅存營運組 |
| `enabled` | 否 | 預設 `true` |

## Body 區域用途

Manifest 的 Markdown body（frontmatter 以下）可自由撰寫補充說明，例如：

- `ai-evaluate` 類型的背景脈絡與判斷準則
- 任務的前置條件或注意事項
- 變更紀錄

營運組在執行 `ai-evaluate` 類型任務時，會將 body 內容連同 prompt 一併提供給 AI。
