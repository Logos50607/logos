---
name: workflow_management
description: "用於指導 AI 如何建立、組織及維護 Antigravity Workflows。當需要定義結構化的步驟、程序或斜線指令時使用。"
---

# Antigravity Workflows 管理指南

本技能旨在指導 AI 遵循 Antigravity 官方規範，建立結構化的「工作流
(Workflows)」。

## 1. 什麼是 Workflows？

Workflows 是結構化的步驟或提示序列，旨在引導 AI 處理複雜任務。它們通常透過
`/slash-commands`（斜線指令）觸發。

## 2. 檔案位址

- **全域工作流**: `~/.gemini/workflows/`
- **專案專屬工作流**: `.agent/workflows/<workflow-name>.md`

## 3. Workflows 文件結構

Workflows 使用 Markdown 格式，並建議包含以下核心元件：

### (1) YAML Frontmatter (選用但建議)

用於定義描述或詮釋資料。

```yaml
---
description: [簡短標題，說明此工作流的功能]
---
```

### (2) 核心內容

- **標題**: 工作流的名稱。
- **描述**: 此工作流欲達成的目標。
- **具體步驟**: 使用編號或列表列出 AI 應遵循的循序指令。

## 4. 工作流鏈接 (Chaining)

一個工作流可以調用另一個工作流，只需在步驟中包含其斜線指令即可（例如：「執行
/another-workflow 以處理後續作業」）。

## 5. 檔案限制

- 格式：Markdown (`.md`)
- 長度：建議不超過 **12,000 字元**。

## 6. 最佳實踐

- **條理清晰**: 步驟應簡單明瞭，一次執行一個邏輯單位。
- **一致性**: 確保所有工作流遵循專案的慣例。
- **台灣正體中文**: 文件應使用台灣正體中文撰寫。
- **腳本模組化**: 工作流所呼叫的底層腳本應維持在 **100
  行以內**。若功能過於龐大應主動切分。
- **索引導航**: 腳本應扮演 **Index / Content List** 角色，引導 AI
  操作特定邏輯。推薦使用 **Pipe (管道)** 或 **Strategy Pattern (策略模式)**
  以注入方式驅動高階邏輯。
