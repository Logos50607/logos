---
name: permission-policy
trigger: always_on
description: "定義各類受限操作的預設允許、拒絕與轉人工規則，供監察組審核時參照。"
---

# 權限政策 (Permission Policy)

## 預設允許（Auto-approve）

| 條件 | type | 說明 |
|------|------|------|
| 組別讀取任意路徑 | bash / read | 讀取不具破壞性 |
| 組別寫入**自身**專案目錄 | write | 各組有權維護自身專案 |
| 組別在**自身**目錄執行腳本 | bash | 限於 working_dir 範圍內 |
| 刪除操作（任意組） | bash | 一律 soft-delete：mv 至 `/tmp/supervision-trash/YYYYMMDD/` |
| 跨組 -p（唯讀查詢，不涉及寫入） | cross-team-p | 資訊查詢無副作用 |

## 預設拒絕（Auto-deny）

- 寫入其他組別的專案目錄（未經授權）
- 修改 git history（`reset --hard`、`push --force` 等）
- 直接寫入 `~/.gemini/.agent/` 或 `~/.claude/`（需走 global discipline 更新流程）

## 轉人工（Escalate）

- 跨組 -p 涉及目標組寫入
- 高風險指令（`sudo`、系統設定修改）
- 跨組 -p 目標組不存在或路徑不明
- 無法歸類的情況

## 審核優先順序

1. Auto-deny → 立即回傳，記錄日誌
2. Soft-delete → mv 備份，記錄日誌（decision: soft-deleted）
3. Auto-approve → 執行，記錄日誌
4. Escalate → 寫入 ASK_HUMAN.md，通知聯絡組
