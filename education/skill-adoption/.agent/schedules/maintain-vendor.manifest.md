---
task_name: education-skill-adoption-maintain-vendor
description: "定期檢查已掛載的 _vendor/ 外部來源狀態，決定更新、退場或內化。"
owner_group: education
owner_project: skill-adoption
schedule:
  type: interval
  expr: "90d"
command:
  type: ai-evaluate
  script_path: scripts/maintain-vendor.sh
  prompt_path: .agent/schedules/prompts/maintain-vendor-eval.prompt.md
  working_dir: /data/logos/education/skill-adoption
retry:
  max_attempts: 1
  delay_seconds: 60
failure:
  notify: escalate
report:
  format: markdown
  destination: records/schedule-reports/
enabled: false
---

# 排程背景說明

本任務定期執行 `scripts/maintain-vendor.sh`，對所有已掛載的 `_vendor/` 外部來源：
1. 蒐集上游更新狀態、引用狀態、adapter 偏離度
2. 由 AI 依據決策邏輯判斷處置方式（更新/退場/內化/維持現狀）

## 前置條件

- `scripts/maintain-vendor.sh` 需已完成實作（目前狀態：⬜ 待建立）
- 排程啟用前將 `enabled` 改為 `true`

## 變更紀錄

- 2026-03-27：建立 manifest，`enabled: false`，待腳本實作後啟用
