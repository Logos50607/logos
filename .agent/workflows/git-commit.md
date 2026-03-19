---
description: 執行標準化的 Git 提交流程，包含變更分析與總結。
---

# /git-commit 工作流

本工作流旨在確保每一次提交都經過充分的變更分析，並產生高品質的提交訊息。

## 執行步驟

1. **變更分析**:
   - 執行 `git diff` 查看本次修改的具體內容。
   - 執行 `git status` 確認目前的暫存區狀態。
   - **確認管理文件**: 評估本次變更是否需要同步更新 rules, skills, workflows,
     `GEMINI.md` 或 `README.md`。

2. **撰寫總結**:
   - 根據 `git diff` 的結果，歸納出本次修改的中心目標。
   - 使用**台灣正體中文**撰寫簡明扼要的提交訊息。
   - 訊息建議包含前綴（如 `feat:`, `fix:`, `doc:`, `chore:`, `refactor:`）。

3. **執行提交**:
   - 執行 `git add .`（除非只需提交特定檔案）。
   - 執行 `git commit -m "[訊息內容]"`。

4. **遠端同步 (Remote Setup & Push)**:
   - **檢查 Remote**: 執行 `git remote`。若無任何遠端，則執行
     `gh repo create $(basename $(pwd)) --private --source=. --remote=origin`。
   - **推送變更**: 執行 `git push origin [branch-name]` (通常為 `master` 或
     `main`)。

5. **歷史紀錄維護 (Squash)**:
   - 檢查近期提交紀錄。若發現連續多個 commit
     屬於同一邏輯變更，應主動請示使用者執行 `squash` 或 `rebase` 操作。
   - **Squash 後推送**: 若執行了 squash/rebase
     修改了歷史，務必確保最終變更已同步推送至遠端。
