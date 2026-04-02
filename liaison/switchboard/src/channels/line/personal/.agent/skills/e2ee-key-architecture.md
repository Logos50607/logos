---
name: e2ee-key-architecture
description: "LINE E2EE 金鑰類型、儲存位置、解密流程完整說明。任何涉及 E2EE 加解密的開發必讀。"
trigger: model_decision
---

# LINE E2EE 金鑰架構

## 金鑰類型分類

| 類型 | 說明 | keyId 範圍 | 儲存位置 |
|------|------|-----------|---------|
| **個人金鑰**（Personal Key） | 每個 LINE 帳號的 Curve25519 key pair | ~600K–6M | LTSM sandbox（wasm）+ IDB `e2ee_public_key` |
| **群組金鑰**（Group Key） | 每個群組/社群的共享 Curve25519 key pair | ~100M–200M | LTSM（需手動解包載入，見下方） |

---

## 個人金鑰

### 儲存位置

- **私鑰**：存在 `ltsm.wasm` 的記憶體內（LTSM sandbox，iframe），透過 `e2eekey_load_key` 載入，slot ID 為小整數（1, 2, 3...）
- **公鑰**：IndexedDB `LINE_COMMON.e2ee_public_key`，格式：`{e2eePublicKey: {keyId, keyData(base64), createdTime(ms str)}}`
- **磁碟快取**：`data/pubkeys.json`，格式：`{keyId_str: {data: base64, createdTime: int_ms}}`

### 載入方式（Python 端）

```python
# 從 IDB 讀取所有已知公鑰（啟動時執行一次）
pub_store = await load_idb_pubkeys(page)  # encrypt_e2ee.py

# 找到私鑰在 LTSM 的 slot（掃描 slot 1–50）
ltsm_slot = await _load_my_key(page, my_mid, key_id)  # encrypt_e2ee.py
```

### 遷移注意

`pubkeys.json` 舊格式為 `{keyId: base64_str}`，新格式為 `{keyId: {data, createdTime}}`。
`sync.py` 啟動時自動遷移（`createdTime=0` 表示未知）。

---

## 群組金鑰

### 儲存位置

- **私鑰**：**不在 LTSM slot 1–50**，也不在任何 IDB。需透過 GW API 取得加密版本再解包
- **解包後**：由 `unwrap_group_key()` 透過 LTSM `e2eechannel_unwrap_group_shared_key` 指令載入 wasm，回傳新的 ltsm_slot_id

### 取得流程

```
getLastE2EEGroupSharedKey(chat_mid)
  → {groupKeyId, creatorKeyId, creator, encryptedSharedKey, receiver, receiverKeyId}

creator 公鑰 → pub_store[creatorKeyId]（通常已存在）

make_decrypt_channel(my_personal_ltsm, creator_pub)
  → channel_ltsm_id（ECDH shared secret）

unwrap_group_key(channel_ltsm_id, encryptedSharedKey)
  → group_ltsm_id（群組私鑰 slot）
```

### GW API

```
POST /api/talk/thrift/Talk/TalkService/getLastE2EEGroupSharedKey
body: [1, chat_mid]   ← 第一個參數 1 = 群組類型

response.data:
  groupKeyId       - 群組金鑰 ID（messages 的 r_key_id）
  creatorKeyId     - 建立金鑰的人的個人 key ID
  creator          - 建立金鑰的人的 mid
  encryptedSharedKey - base64，用 ECDH channel 加密的群組私鑰
  receiver/receiverKeyId - 接收者（通常是自己）
```

### 快取策略

```python
# ltsm_cache 同時存個人金鑰和群組金鑰
ltsm_cache = {
    2705364:   1,    # 個人金鑰 → LTSM slot 1
    154774569: 7,    # 群組金鑰（泰好吃）→ LTSM slot 7（解包後）
    146321923: 8,    # 群組金鑰（彭邊孔呆丸）→ LTSM slot 8
}
# 值為 -1 表示此 session 載入失敗，不再重試
```

---

## 訊息解密方向

### 1-to-1 訊息

| 我是 | my_key_id | other_key_id | other_mid |
|------|-----------|-------------|-----------|
| 接收方 | `r_key_id`（我的個人金鑰） | `s_key_id` | `sender_mid` |
| 發送方 | `s_key_id`（我的個人金鑰） | `r_key_id` | `to` |

### 群組訊息（`to` 以 C 或 R 開頭）

**所有群組訊息（無論誰發送）固定格式：**

| 欄位 | 值 |
|------|-----|
| `r_key_id` | 群組金鑰 ID（所有訊息相同，如 154774569） |
| `s_key_id` | 發送者個人金鑰 ID |
| `my_key_id` | = `r_key_id`（群組私鑰） |
| `other_key_id` | = `s_key_id`（發送者個人公鑰） |
| `other_mid` | 發送者 mid（取 sender's public key 建立 channel） |

**Channel 計算：** `ECDH(group_private, sender_public)` = 與加密時的 `ECDH(sender_private, group_public)` 結果相同

---

## LTSM sandbox 指令對照

| 指令字串 | 用途 | 輸入 | 輸出 |
|---------|------|------|------|
| `decrypt_with_storage_key` | 解密 localStorage 私鑰 | encrypted bytes | private key bytes |
| `e2eekey_load_key` | 載入私鑰 bytes → wasm | keyBytes (Uint8Array) | ltsm_slot_id |
| `e2eekey_get_key_id` | 查 slot 對應的 keyId | ltsm_slot_id | keyId (int) |
| `e2eekey_create_channel` | ECDH：我的私鑰 + 對方公鑰 | (ltsm_slot_id, pubKeyBytes) | channel_ltsm_id |
| `e2eechannel_unwrap_group_shared_key` | 解包群組私鑰 | (channel_ltsm_id, encKeyBytes) | group_ltsm_id |
| `get_hmac` | 計算 X-Hmac | (token, path, body) | hmac_base64 |

---

## 常見失敗原因

| 症狀 | 原因 | 解法 |
|------|------|------|
| 個人訊息解密失敗，ltsm_cache 有 -1 | page reload 後 LTSM slot 重新分配 | `_refresh_token` 時清除 ltsm/chan cache |
| 群組訊息全部解密失敗 | r_key_id 是群組金鑰，不在 LTSM 1–50 slots | 呼叫 `load_group_key()` 解包 |
| API 回傳 `unable to find midType` | body 格式錯，缺少類型參數 | `getLastE2EEGroupSharedKey` body 需 `[1, chat_mid]` |
| 解密後 authentication failure | 金鑰輪換，消息用了已不存在的老金鑰 | 設 `_decrypt_skip=True`，無法修復 |
</content>
