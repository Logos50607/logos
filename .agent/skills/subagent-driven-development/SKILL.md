---
name: subagent-driven-development
description: "使用 subagent 平行執行實作計畫：每工作派遣新 agent，搭配兩階段審核（規格遵守 → 程式碼品質）。"
trigger: model_decision
---

# Subagent-Driven Development

> 原始來源：`.agent/skills/_vendor/superpowers/skills/subagent-driven-development/SKILL.md`

## 觸發時機

有實作計畫、工作大多獨立、且要留在當前對話中執行時使用。

- 無實作計畫 → 先用 brainstorming + writing-plans。
- 工作密切耦合 → 手動執行或先拆解。

## 核心原則

每工作新 agent + 兩階段審核（規格遵守先，品質次）= 高品質、快速迭代。

## 流程

1. **讀取計畫**：提取所有工作的完整文字、記錄背景。
2. **逐工作執行**：
   - 派遣 implementer subagent（提供完整工作文字 + 背景，不讓 subagent 自己讀計畫檔）。
   - Implementer 有問題 → 回答並提供背景。
   - Implementer 完成後 → 派遣規格審核 subagent。
   - 規格審核通過 → 派遣程式碼品質審核 subagent。
   - 審核未通過 → implementer 修復 → 再審，直至通過。
3. **所有工作完成後**：派遣最終程式碼審核。

## 處理 Implementer 狀態

| 狀態 | 處置 |
|------|------|
| DONE | 進入規格審核 |
| DONE_WITH_CONCERNS | 讀疑慮，正確性問題先解決再審核 |
| NEEDS_CONTEXT | 提供遺失背景，重派同模型 |
| BLOCKED | 評估：上下文不足？重派更強模型？工作太大？計畫有誤？ |

## 模型選擇

- 機械性工作（隔離函數、清晰規格、1-2 檔）→ 快速模型。
- 整合工作（多檔協調、模式比對）→ 標準模型。
- 架構、設計、審核 → 最強模型。

## 紅旗 — 絕不

- 跳過任何審核階段。
- 在規格審核前開始品質審核（順序錯誤）。
- 平行派遣多個 implementer（會衝突）。
- 讓 subagent 自己讀計畫檔（改提供完整文字）。
- 審核有未解決問題時移至下一工作。
- 忽視 subagent 的提問或 BLOCKED 狀態。

## 本地化調整

- Subagent 的 implementer 應遵循 `test-driven-development` skill。
- 審核員應參照 `development_guidelines` rule 中的品質要求。
- 提交訊息遵循 `git_usage` rule（台灣正體中文、含前綴）。
- 此 skill 與組織的團隊架構概念一致：每工作的 subagent 類比各組別的專責 agent。
