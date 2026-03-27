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

2. **目錄結構檢查與建立**:
   - 檢查並建立根目錄必要的管理檔案：`.agent/rules`, `.agent/skills`,
     `.agent/workflows`, `README.md`, `AGENT_PLAN.md` 及 `ASK_HUMAN.md`。
   - **注意**：不再建立 `GEMINI.md`，其索引功能由 `.agent/INDEX.md` 或直接讀取
     `.agent/rules` 取代。

3. **初始化文件更新**:
   - 在 `README.md` 中新增「專案初始化紀錄」區塊，標記初始化日期與狀態。

4. **自動同步 Disciplines**:
   - // turbo 執行工作流 `/sync-disciplines` 或直接執行同步腳本：
     `bash /home/logos/.gemini/.agent/skills/sync_disciplines_project/scripts/sync.sh`
   - 確保 `.claude/CLAUDE.md` 及相關命令已就緒。

5. **確認與回報**:
   - 回報專案結構與同步狀態。
