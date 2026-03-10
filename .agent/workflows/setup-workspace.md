---
description: 初始化或檢查工作區結構與管理清單
---

# /setup-workspace 工作流

本工作流旨在確保工作區符合專案規範結構，並建立必要的管理檔案。

## 執行步驟

1. **目錄結構檢查**:
   - 檢查根目錄是否包含 `.agent/rules`, `.agent/skills`, `.agent/workflows`。
   - 若缺失，主動建議建立或直接建立（若使用者授權）。

2. **管理清單檢查**:
   - 檢查根目錄是否包含 `TODOLIST.md` 及 `ASKHUMAN.md`。
   - 若缺失，建立符合規範格式的檔案。

3. **初始化文件內容**:
   - 確保 `TODOLIST.md` 包含第一條紀錄並符合 `YYYY-MM-DD` 格式。
   - 確保 `ASKHUMAN.md` 已備妥。

4. **讀取專案背景**:
   - 讀取根目錄的 `README.md` 以了解專案目標。

5. **確認與回報**:
   - 回報工作區結構完整性，並在 `TODOLIST.md` 新增初始化紀錄。
