# DEPENDENCIES

| 依賴 | 版本 | 用途 | 安裝／檢查 |
|------|------|------|-----------|
| jq | 任意 | claude/hooks/ 解析 hook JSON（**選用**：無 jq 時腳本以 grep/sed 保守解析） | `command -v jq`；`sudo apt install jq` |
| git | 任意 | stop-uncommitted-reminder.sh 偵測工作區狀態；dotfiles 本身版控 | `command -v git` |
