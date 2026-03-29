---
name: permission-policy
trigger: always_on
description: "定義各類受限操作的預設允許與拒絕規則，供監察組審核時參照。"
---

# 權限政策 (Permission Policy)

## 預設允許（Auto-approve）

符合以下條件可直接允許，無需人工介入：

| 條件 | 允許的 tool | 說明 |
|------|------------|------|
| 組別寫入**自身**專案目錄（`working_dir` 在請求方組別路徑下） | `Write` | 各組有權維護自身專案 |
| 組別在**自身**專案目錄執行腳本 | `Bash` | 限於 working_dir 範圍內 |
| 讀取任意路徑 | `Read`, `Glob`, `Grep` | 讀取操作不具破壞性 |

## 刪除操作（Soft-delete，備份至 tmp）

所有刪除請求一律**不直接 rm**，改為移動至備份目錄後視為完成：

```sh
BACKUP=/tmp/supervision-trash/$(date +%Y%m%d)
mkdir -p "$BACKUP"
mv <target_file> "$BACKUP/"
```

- 備份路徑：`/tmp/supervision-trash/YYYYMMDD/<filename>`
- 視為 auto-approve，記錄至稽核日誌（decision: soft-deleted）
- `/tmp` 由 OS 定期清理；若需永久保留請改用其他路徑

## 預設拒絕（Auto-deny）

以下操作直接拒絕，不轉人工：

- 寫入其他組別的專案目錄（未經該組授權）
- 修改 git history（`reset --hard`、`push --force` 等）
- 寫入 `~/.gemini/.agent/` 或 `~/.claude/`（global disciplines 的 SSOT）

## 轉人工（Escalate to human）

無法歸類至上述規則的情況，轉聯絡組通知使用者：

- 跨組寫入但有合理說明
- 涉及外部服務或網路操作
- 高風險指令（`sudo`、系統設定修改等）

## 審核優先順序

1. Auto-deny（立即回傳，不記錄詳細原因）
2. Auto-approve（記錄至稽核日誌，重執行）
3. Escalate（寫入 ASK_HUMAN.md，通知聯絡組）
