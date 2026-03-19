---
description: "將當前專案的 antigravity disciplines (.agent/) 同步至 Claude Code 的 .claude/ 資料夾。"
---

# /sync-disciplines 工作流

將當前專案的 `.agent/rules` 與 `.agent/workflows` 同步進 `.claude/`，
讓 Claude Code 可以吃到專案層級的 disciplines。

## 執行步驟

1. **確認專案根目錄**：
   - 執行 `git rev-parse --show-toplevel` 確認根目錄。
   - 確認 `.agent/` 存在，否則提示使用者先執行 `/setup-project`。

2. **執行同步**：
   ```bash
   bash /home/logos/.gemini/.agent/skills/sync_disciplines_project/scripts/sync.sh
   ```

3. **確認結果**：
   - 確認 `.claude/CLAUDE.md` 已包含 rules 內容。
   - 確認 `.claude/commands/` 已軟連結至 `.agent/workflows`。

4. **提示後續**：
   - 告知使用者同步完成，Claude Code 重新載入後即生效。
   - 提醒：更新 `.agent/rules` 或 `.agent/workflows` 後需重新執行此 workflow。
