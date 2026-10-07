---
name: claude-hooks
description: "Claude Code hooks：以機制強制執行 disciplines（sudo 攔截、未 commit 提醒）。"
---

# Claude Code Hooks

## 核心目標

把「靠模型自律」的 disciplines 變成 harness 層的強制機制（依據：discipline_metadata §3「機制優先於條文」；決策紀錄見 education/global-disciplines/reports/discipline-proposals/2026-07-07-mechanism-upgrade.md）。

## 結構索引

| 檔案 | 強制的規則 | 行為 |
|------|-----------|------|
| `hooks/pretooluse-deny-sudo.sh` | agent_behavior §4 提權邊界 | PreToolUse(Bash)：攔截 agent 自行執行 sudo，deny 並要求交給使用者以 `! <指令>` 執行 |
| `hooks/stop-uncommitted-reminder.sh` | git_usage §1 即時提交 | Stop：偵測 cwd 有未 commit 變更時 block 一次提醒；`stop_hook_active` 防無限迴圈 |
| `hooks/test_*.sh` | — | 測試（pipe 範例 JSON 進腳本驗證） |
| `settings-baseline.json` | 對話紀錄保留 | 各機共用的 settings 基準值（目前：`cleanupPeriodDays: 3650`，避免預設 30 天自動刪除 transcript） |
| `apply-settings.sh` | — | 把 baseline 冪等合併進 `~/.claude/settings.json`（保留既有 hooks 等其他鍵，備份為 `.bak`） |
| `test_apply_settings.sh` | — | 驗證合併、保留既有鍵、冪等 |

## 使用指南

1. 腳本以**絕對路徑**登記於 `~/.claude/settings.json` 的 `hooks` 區塊（不需 symlink）：

```json
"hooks": {
  "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "/data/logos/internal-control/dotfiles/claude/hooks/pretooluse-deny-sudo.sh"}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "/data/logos/internal-control/dotfiles/claude/hooks/stop-uncommitted-reminder.sh"}]}]
}
```

2. 新機器或重建後執行 `sh apply-settings.sh` 套用 baseline；新增共用設定只需改 `settings-baseline.json`。
3. **hooks 與 settings 於新 session 才生效**（settings 在 session 啟動時載入）。
4. 測試：`sh hooks/test_pretooluse_deny_sudo.sh && sh hooks/test_stop_uncommitted.sh && sh test_apply_settings.sh`
5. 若 Stop 提醒在長期 dirty 的 repo 中過吵：優先把該 repo 清乾淨（這正是規則的本意）；真要停用，從 settings.json 移除 Stop 區塊即可。

## 實作原理

- 兩腳本皆讀 stdin 的 hook JSON；jq 優先解析，無 jq 時 grep/sed 保守解析（sudo 攔截採「寧誤攔不漏攔」）。
- deny/block 皆以 stdout JSON 回應 harness；放行則 exit 0 無輸出。
- 依賴見 `../DEPENDENCIES.md`（jq 為選用，有 fallback）。
