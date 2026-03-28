---
name: allowed_commands
trigger: always_on
description: "列舉在內控組專案下，AI 可直接執行而不需請示使用者的指令範疇。"
---

# 免請示指令策略 (Allowed Commands Policy)

本規則定義在 `/data/logos/internal-control/` 範疇內，AI 可自主執行的指令。
對應的執行層授權記錄於 `.claude/settings.json`。

## 可直接執行（不需請示）

### Git 唯讀查詢
- `git status`
- `git log`
- `git diff`

### 測試腳本
- `bash dotfiles/test_install.sh` — dotfiles 安裝測試（不修改家目錄）

### Secret 查詢
- `bash scripts/get-secret.sh <name> <requester>` — 白名單控管的唯讀金鑰介面

### 系統資訊
- `ls`、`cat`、`which`、`echo` 等純輸出指令

## 必須請示才能執行

| 操作 | 原因 |
|------|------|
| `bash dotfiles/install.sh` | 修改家目錄 symlink，影響系統環境 |
| `git commit` / `git push` | 版本變更為不可逆操作 |
| 修改 `whitelist.json` | 異動 secret 存取授權清單 |
| 修改 `secrets/` 目錄下任何檔案 | 機密資料操作 |
| `rm` / `mv` 任何檔案 | 破壞性操作 |
