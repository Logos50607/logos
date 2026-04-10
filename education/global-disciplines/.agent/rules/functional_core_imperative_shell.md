---
name: functional_core_imperative_shell
trigger: always_on
description: "純計算與副作用分離：pure function 不做 I/O，orchestrator 不做業務邏輯。又稱 Functional Core / Imperative Shell。"
---

# Functional Core / Imperative Shell

## 核心規則

**純計算與副作用必須分離，不得混在同一個函式或模組中。**

- **Functional Core（純計算）**：相同輸入永遠回傳相同輸出，無任何副作用（不呼叫網路、不讀寫 DB、不讀時間、不產生 random）
- **Imperative Shell（副作用層）**：負責 I/O、協調順序、呼叫 core 並傳遞結果，本身不含業務邏輯

## 副作用的種類

I/O 只是副作用的一種，以下都屬於副作用，不應出現在 core 裡：
- 網路呼叫、資料庫讀寫、檔案讀寫
- 讀取當前時間（`datetime.now()`、`Date.now()`）
- 亂數生成
- 全域狀態修改
- Logging（嚴格來說）

## 為什麼

- Core 可以用純 unit test 驗證，不需要 mock、不需要 async、不需要真實服務
- Shell 的職責清楚：它只知道「呼叫誰」和「傳什麼」，不感知業務細節
- 新增功能時，通常只需擴充 core，不需要動 shell

## 典型結構

```
Shell（有副作用）
  → 取得原始資料（I/O）
  → 傳給 Core 計算（pure）
  → 把結果寫出去（I/O）
```

## 範例

```python
# ❌ 混在一起
async def sync_messages():
    raw = await client.fetch()      # I/O
    result = normalize(raw)         # 計算
    await db.upsert(result)         # I/O

def normalize(raw):
    now = datetime.now()            # 副作用：時間
    return {..., "synced_at": now}

# ✅ 分離
def normalize(raw: dict) -> dict:   # Core：純計算
    return {"external_id": raw["id"], "text": raw.get("text")}

async def sync_messages():          # Shell：協調副作用
    raw = await client.fetch()
    result = normalize(raw)
    await db.upsert(result)
```

## 命名慣例

- Core 方法：`adapt_*`、`normalize_*`、`parse_*`、`validate_*`、`compute_*`
- Shell 方法：`sync_*`、`fetch_and_store_*`、`execute_*`、`run_*`
