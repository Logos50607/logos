---
name: using-git-worktrees
description: "建立隔離 git worktree 工作空間：自動偵測目錄、驗證 .gitignore、安裝依賴、驗證測試基線。"
trigger: model_decision
---

# Using Git Worktrees

> 原始來源：`.agent/skills/_vendor/superpowers/skills/using-git-worktrees/SKILL.md`

## 觸發時機

啟動需隔離的功能開發，或執行實作計畫前。

## 目錄選擇流程（依序檢查）

1. **檢查現存目錄**：
   ```bash
   ls -d .worktrees 2>/dev/null   # 優先（隱藏）
   ls -d worktrees 2>/dev/null    # 替代
   ```
   兩者都存在時 `.worktrees` 優先。

2. **檢查專案設定**：grep CLAUDE.md 或 README.md 中的 worktree 目錄偏好。

3. **詢問使用者**：若以上皆無，提供選項讓使用者決定。

## 安全驗證（專案本地目錄）

建立 worktree 前**必須**確認目錄被 `.gitignore` 忽略：

```bash
git check-ignore -q .worktrees 2>/dev/null
```

若未被忽略 → 添加至 `.gitignore` 並提交，再繼續。

## 建立步驟

```bash
# 1. 偵測專案名
project=$(basename "$(git rev-parse --show-toplevel)")

# 2. 建立 worktree
git worktree add "$WORKTREE_DIR/$BRANCH_NAME" -b "$BRANCH_NAME"
cd "$WORKTREE_DIR/$BRANCH_NAME"

# 3. 自動偵測並安裝依賴
[ -f package.json ] && npm install
[ -f Cargo.toml ] && cargo build
[ -f requirements.txt ] && pip install -r requirements.txt
[ -f pyproject.toml ] && poetry install
[ -f go.mod ] && go mod download

# 4. 執行測試驗證基線
# 使用專案對應的測試指令
```

## 基線測試

- 測試通過 → 報告就緒。
- 測試失敗 → 報告失敗，詢問使用者是否繼續或調查。
- **絕不**在測試失敗時靜默繼續。

## 快速參考

| 情況 | 處置 |
|------|------|
| `.worktrees/` 存在 | 使用它（驗證 gitignore） |
| 都不存在 | 檢查設定 → 詢問使用者 |
| 目錄未被忽略 | 加入 `.gitignore` + 提交 |
| 基線測試失敗 | 報告 + 詢問 |

## 本地化調整

- 提交訊息遵循 `git_usage` rule。
- 與 `writing-plans`、`subagent-driven-development` 搭配：先建 worktree，再於其中執行計畫。
