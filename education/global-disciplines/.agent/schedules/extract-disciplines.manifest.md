---
task_name: "education-global-disciplines-extract"
description: "掃描近期各組 Claude 對話 session，提取可沉澱為 global/project discipline 的模式，產出草稿供審核"
owner_group: "education"
owner_project: "global-disciplines"

schedule:
  type: "interval"
  expr: "1d"

command:
  type: "ai-evaluate"
  script_path: "scripts/collect-sessions.sh"
  prompt_path: ".agent/schedules/prompts/extract-disciplines.prompt.md"
  working_dir: "/data/logos/education/global-disciplines"

retry:
  max_attempts: 1
  delay_seconds: 60

failure:
  notify: "log"

report:
  format: "markdown"
  destination: "reports/discipline-proposals"

enabled: true
---

## 背景說明

本任務每日掃描 `~/.claude/projects/` 下所有組別的新 session，提取出值得沉澱為 discipline 的模式與決策。

AI 評估產出的草稿存放於 `reports/discipline-proposals/`，由使用者或教育組 agent 決定是否正式提交至 `~/.gemini/.agent/`。

## 評估準則

- 只建議具備**通用性**的模式，不建議僅對單一任務有效的做法
- 若同一模式已有對應 discipline，不重複建議
- 草稿應達到「可直接放入 .agent/rules/ 使用」的顆粒度
