---
name: brainstorming
description: "在任何創意工作或功能開發前，透過協作對話釐清需求、探索方案並產出設計規格。強制需求釐清，未經使用者核可設計前不得進入實作。"
trigger: model_decision
---

# Brainstorming

> 原始來源：`.agent/skills/_vendor/superpowers/skills/brainstorming/SKILL.md`

## 觸發時機

在建立功能、構建元件、添加功能或修改行為**之前**必須使用。

## 核心流程

1. **探索專案背景**：檢查相關檔案、文件、最近 commit，理解現狀。
2. **逐一提出澄清問題**：一次一個問題，優先使用多選題，避免假設。
3. **提案方案**：提出 2-3 種方法並權衡取捨。
4. **段落式呈現設計**：將設計以易讀段落呈現，取得使用者認可。
5. **寫入設計文件**：儲存至 `docs/specs/YYYY-MM-DD-<topic>-design.md`（或專案慣用位置）。
6. **規格自我檢視**：確認設計完整後，由使用者審查。
7. **銜接實作**：設計核可後，調用 writing-plans skill 建立實作計畫。

## 硬性門檻

**未獲使用者設計認可前，絕對不能執行任何實作、寫程式碼或搭建專案。**

簡單專案也需設計。簡單專案正是未檢查假設導致浪費最多工作的地方。

## 設計原則

- **YAGNI**：無情地砍掉不需要的功能。
- **隔離與清晰**：將系統分解為較小單位，每個有明確目標與定義良好的介面。
- **增量驗證**：每個設計決策都可獨立驗證。
- **探索替代方案**：不要鎖定第一個想到的方案。

## 本地化調整

- 設計文件使用台灣正體中文撰寫。
- 與現有 `development_guidelines` rule 搭配：設計階段遵循本 skill，實作階段遵循 development_guidelines。
- 設計產出後，可銜接 `writing-plans` skill 建立計畫，再由 `subagent-driven-development` 執行。
