---
trigger: always_on
description: "README 優先原則，要求 AI 主動讀取並維護各目錄下的 README.md，以確保專案背景資訊同步。"
---

# README 管理規範 (README Management)

本規則旨在確保專案各層級的開發背景、結構與使用方法都能透過 `README.md`
得到妥善記錄。**README 文件必須幫助使用者、開發者與 AI
快速理解該工具或功能想解決什麼問題、如何使用、以及運作原理。**

## 1. README 優先原則 (Read First)

- **主動讀取**：在對話開始、分析新功能或進入任何子目錄時，AI
  **必須優先讀取**該目錄下的 `README.md`。

## 2. 維護與更新職責 (Maintenance)

- **主動評估**：每次執行工作任務時，AI 應評估是否需要更新受影響目錄的
  `README.md`。
- **維護職責**：確保記錄內容與實際程式碼邏輯同步，以便後續開發者或 AI 理解。

## 3. 內容品質要求 (Content Requirements)

每個 `README.md` 應至少包含以下要素：

- **核心目標 (Core Goal)**：清晰描述該目錄及其轄下檔案旨在「解決什麼問題」。
- **結構索引 (Structure
  Index)**：列出該目錄的主要檔案與子資料夾，提供簡要功能概述。
- **使用指南 (Usage
  Guide)**：說明「如何使用」該功能或工具，包含前置作業、執行指令、參數說明或注意事項。
- **實作原理 (Implementation
  Details)**：簡述「運作原理」與核心邏輯，幫助開發者與 AI 理解其內部流程。
