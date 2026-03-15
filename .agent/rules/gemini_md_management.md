---
name: gemini_md_management
trigger: always_on
description: "規範專案根目錄下 GEMINI.md 的內容與結構，確保專案具備自述性與索引功能。"
---

# GEMINI.md 管理規範 (GEMINI.md Management)

本規則旨在確保每個專案的根目錄都具備 `GEMINI.md`
檔案，作為該專案的初始化狀態紀錄以及規則、技能、工作流的索引。

## 1. 強制性要求

- **存在性**：每個專案的根目錄 **必須** 存在 `GEMINI.md`。
- **維護職責**：AI 在執行任務時，若發現 `GEMINI.md`
  缺失或內容過時，應主動建立或更新。

## 2. 內容結構

`GEMINI.md` 必須包含以下兩大核心部分：

### 2.1 專案初始化狀態

- 記錄專案是否已完成初始化（如：執行過 `/setup-project`）。
- 應在 YAML frontmatter 或開頭段落明確標示 `status: initialized` 或類似狀態。

### 2.2 Metadata 清單與概述

- **格式要求**：格式必須與 Global 的 `GEMINI.md` 一致。
- **列出內容**：應列出該專案專屬（位於 `.agent/` 目錄下）的所有 rules, skills,
  與 workflows。
- **描述方式**：採用「檔案或資料夾名稱：使用情境或功能概述」的條列格式。

## 3. 範例格式

```markdown
---
name: project_name_index
status: initialized
description: "專案概述..."
---

# 專案管理索引 (Project Index)

## 1. rules (規則)

- **custom_rule.md**: 在處理 X 邏輯時遵循。

## 2. Workflows (工作流)

- **[/custom-task]**: 執行 Y 自動化流程。

## 3. Skills (技能)

- **[custom_skill]**: 用於處理 Z 任務的專用技能。
```
