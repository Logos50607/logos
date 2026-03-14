---
name: setup-project
description: 初始化或檢查專案結構與管理清單
---

# /setup-project 工作流

本工作流旨在確保專案符合專案規範結構，並建立必要的管理檔案。

## 執行步驟

1. **Git 初始化檢查**:
   - 檢查目錄是否已由 Git 管理（是否存在 `.git` 目錄）。
   - 若尚未初始化，應執行 `git init`。

2. **目錄結構檢查**:
   - 檢查根目錄是否包含 `.agent/rules`, `.agent/skills`, `.agent/workflows`,
     `GEMINI.md`, `README.md`, `AGENT_PLAN.md` 及 `ASK_HUMAN.md`。
   - 若缺失，應直接建立。

3. **確認與回報**:
   - 回報專案結構完整性，並在 `GEMINI.md` 新增初始化紀錄。
