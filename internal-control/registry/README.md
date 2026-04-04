---
name: registry
description: "Secrets 存取控管：白名單授權、存取紀錄、異常通知（規劃中）。"
---

# Registry — Secrets 存取控管

## 核心目標

確保 `~/.logos/secrets/` 下的機密只能被授權的 consumer 存取，並留下完整稽核紀錄。

## 現況（已實作）

| 元件 | 檔案 | 說明 |
|------|------|------|
| 存取閘道 | `scripts/get-secret.sh` | 唯一合法的金鑰取用介面，非白名單直接拒絕 |
| 白名單 | `whitelist.json` | 定義每個 secret 允許哪些 consumer 存取 |
| 存取紀錄 | `registry/access.log` | 每次成功存取都記一筆 `timestamp\tconsumer\tsecret` |

### 白名單格式

```json
{
  "name": "secret 名稱",
  "description": "用途說明",
  "type": "path | file",
  "path": "相對於 SECRETS_DIR 的路徑",
  "consumers": ["組別/模組"]
}
```

### 使用方式

```sh
# 取得 secret 內容或路徑
/data/logos/internal-control/scripts/get-secret.sh <secret-name> <requester>

# 範例
/data/logos/internal-control/scripts/get-secret.sh line-official-channel-token liaison/switchboard
```

## 尚未實作（藍圖）

### 異常通知
- 被拒絕的存取（exit code 2）目前只記 stderr，沒有通知
- 目標：被拒絕 → 寫入 `registry/denied.log` → 觸發 LINE 通知

### 定期稽核報告
- 目標：每週彙整 `access.log`，用 LINE 推送摘要給管理者
- 格式：「過去 7 天，哪些 consumer 存取了哪些 secret 幾次」

### 整合 cloud-monitor
- `registry` 通知 + `cloud-monitor` 通知共用同一個 LINE 通知介面
- 見 `cloud-monitor/README.md`
