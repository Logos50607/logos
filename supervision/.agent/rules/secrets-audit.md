---
name: secrets-audit
trigger: always_on
description: "監察組職責：稽核所有金鑰取用行為，確保唯一入口原則，禁止任何直接讀取 secrets 目錄的行為。"
---

# Secrets 存取稽核規範

## 唯一入口原則

所有金鑰、cookie、token 的存取**必須且只能**透過：

```
internal-control/scripts/get-secret.sh <secret-name> <requester>
```

任何直接讀取 `$SECRETS_DIR`（`~/.logos/secrets/`）路徑的程式碼或腳本均屬**違規**。

## 監察組的稽核職責

### Code Review 時檢查

審查任何 PR 或程式碼變更時，必須確認：

- [ ] 沒有硬編碼 secret 路徑（如 `~/.logos/secrets/...`、`$SECRETS_DIR/...`）
- [ ] 沒有直接讀取 `secrets/` 目錄的腳本（`cat`、`open`、`read` 等）
- [ ] 新增的 secret 已在 `internal-control/whitelist.json` 登記
- [ ] 消費方已列入對應 secret 的 `consumers` 白名單
- [ ] 消費方的 `DEPENDENCIES.md` 已記錄 secret 依賴

### 定期稽核

定期比對 `internal-control/registry/access.log` 與 `whitelist.json`：
- 有存取紀錄但不在白名單 → 立即警示
- 白名單中的 consumer 長期無存取紀錄 → 可考慮移除

### 違規處理

發現違規時，寫入 `supervision/ASK_HUMAN.md`：
```
- [ ] YYYY-MM-DD [SECRETS VIOLATION] <路徑>:<行號> 直接存取 <secret>，應改用 get-secret.sh
```
