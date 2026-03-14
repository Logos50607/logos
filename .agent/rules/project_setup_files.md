---
name: project_setup_files
trigger: always_on
description: "專案結構與管理清單規範，定義了 .agent 目錄、GEMINI.md 以及 TODOLIST/ASKHUMAN 的用途。"
---

# 專案結構與清單規範 (Project Setup & Lists)

本規則旨在確保專案結構化，並透過清單管理 AI 與使用者的互動。

## 1. 核心結構

- `.agent/rules/`：存放專案規範。
- `.agent/skills/`：存放專案輔助技能。
- `.agent/workflows/`：存放 slash commands 及自動化流程。
- `GEMINI.md`: rules, skills, 與 workflows
  的索引；其格式為「檔案或資料夾名稱：使用情境」。
- `README.md`：參照 global 的 readme rule 建立。

## 2. 管理清單 (TODOLIST)

在專案根目錄必須始終維護下列管理清單 (TODOLIST)：

- **`AGENT_PLAN.md`**：記錄 AI 計畫執行的事項。
- **`ASK_HUMAN.md`**：記錄需請示使用者的項目、衝突或未驗收的任務。
- **格式規範**：遵循 `todolist_format.md`。

## 3. README 優先原則

- **主動讀取**：對話開始、分析功能或進入子目錄時，優先讀取該目錄下的
  `README.md`。
- **維護職責**：確保 `README.md`
  清楚說明目錄結構、程式碼邏輯及使用方式，以便後續開發。
