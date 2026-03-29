---
name: line-e2ee-v2-media
trigger: model_decision
description: "LINE E2EE V2 圖片與影片傳送的協議細節與已知坑點，實作 send_image.py / send_video.py 時必讀。"
---

# LINE E2EE V2 媒體傳送協議

## SID 對應

| 媒體類型 | contentType | SID | OBS 路徑 |
|----------|-------------|-----|----------|
| 圖片 | 1 | `emi` | `/r/talk/emi/` |
| 影片 | 2 | `emv` | `/r/talk/emv/` |
| 音訊 | 3 | `ema` | `/r/talk/ema/` |
| 檔案 | 4 | `emf` | `/r/talk/emf/` |

## 加密共用流程（圖片與影片相同）

```
keyMaterial (32B random)
  → HKDF-SHA256(salt=b'', info=b'FileEncryption', length=76)
  → encKey[0:32] / macKey[32:64] / nonce[64:76]
  → AES-CTR(counter=nonce+\x00\x00\x00\x00) 加密
  → 附加 HMAC（格式見下方）
```

## HMAC 格式差異（最重要的坑）

### 圖片、縮圖、preview（single HMAC）
```
HMAC-SHA256(macKey, ciphertext)
```

### 影片主體（chunked HMAC）
```
chunk_hashes = concat(SHA-256(每個 128KB chunk of ciphertext))
HMAC-SHA256(macKey, chunk_hashes)
```

來源：extension JS `CL(file, km, BP(t))`，`BP(t) = e.type === EU.VIDEO`，
`SL()` 分塊、`qI()` 串接、`TL()` HMAC。

## OBS 上傳順序

### 圖片
1. POST `/r/talk/emi/{reqid}` → 取 `x-obs-oid`
2. POST `/r/talk/emi/{oid}__ud-preview`（同份加密資料）

### 影片（三步缺一不可）
1. POST `/r/talk/emv/{reqid}` → 取 `x-obs-oid`
2. POST `/r/talk/emv/{oid}__ud-preview`（加密縮圖，第一幀 JPEG）
3. POST `/r/talk/emv/{oid}__ud-hash`（chunk hash list raw bytes）

`ud-hash` 內容：
```python
chunk_hashes = b''.join(
    hashlib.sha256(ciphertext[i:i+131072]).digest()
    for i in range(0, len(ciphertext), 131072)  # ciphertext 不含尾端 32B HMAC
)
```

## contentMetadata 結構

### 圖片
```json
{
  "e2eeVersion": "2", "SID": "emi", "OID": "<oid>",
  "FILE_SIZE": "<原始大小>",
  "MEDIA_CONTENT_INFO": "{\"onObs\":true,\"category\":\"original\",\"animated\":false,\"extension\":\"png\",\"fileSize\":<N>,\"width\":<W>,\"height\":<H>}",
  "MEDIA_THUMB_INFO": "{\"width\":<W>,\"height\":<H>}"
}
```

### 影片
```json
{
  "e2eeVersion": "2", "SID": "emv", "OID": "<oid>",
  "FILE_SIZE": "<原始大小>",
  "DURATION": "<毫秒>",
  "MEDIA_THUMB_INFO": "{\"width\":<W>,\"height\":<H>}"
}
```
注意：影片**沒有** `MEDIA_CONTENT_INFO`。

## encrypt_message content_type

```python
# 圖片
chunks = await encrypt_message(..., content_type=1)
# 影片
chunks = await encrypt_message(..., content_type=2)
```

content_type 影響 E2EE AAD；傳錯會讓收件方解密失敗（出現「備份及復原」錯誤）。

## 症狀對照表

| 症狀 | 原因 | 解法 |
|------|------|------|
| 圖片佔位符無縮圖、無法點開 | 缺 `ud-preview` | 上傳同份加密資料至 `{oid}__ud-preview` |
| 圖片「備份及復原」錯誤 | `content_type=0`（應為 1） | `encrypt_message(..., content_type=1)` |
| 偶發 `REQUEST_INVALID_HMAC` | `compute_hmac` 捕到殘留 JSON 回應 | 過濾 `d.data.startsWith('{')` |
| 影片「基於安全考慮無法看」 | 影片 HMAC 用 single 而非 chunked | 改用 chunked HMAC（見上方） |
| 影片下載可播、inline 轉圈 | 缺 `ud-hash` | 上傳 chunk hashes 至 `{oid}__ud-hash` |
| 影片無縮圖 | 缺 `ud-preview` | 擷取第一幀 JPEG 加密後上傳 |
