---
name: digest
description: "聯絡組訊息摘要模組：定期掃描各 channel、分類評級訊息，並於特定時機呈報給使用者。"
---

# Digest

定期從各 channel 收集訊息，分類評級後，在適當時機透過適當 channel 呈報給使用者。

## 核心目標

1. **掃描**：依設定定期讀取各 channel 的新訊息
2. **分類**：根據分類規則為每則訊息標記類別與優先級
3. **呈報**：按呈報策略將摘要推送給使用者

## 設計原則

- **不與特定資料耦合**：channel 清單、分類規則、呈報目標全部從 `.env` 或設定檔讀入，discipline 只定義規則格式
- **資料以 symlink 或路徑指向外部**：實體資料存於各 channel 服務，本模組只讀取，不儲存原始訊息
- **薄包裝**：本模組不重新實作訊息擷取邏輯，直接呼叫各 channel 的 API

## 資料庫設計

digest 維護自己的 PostgreSQL，**不與 liaison-channel 共用**。

- **liaison-channel**：純紀錄層，忠實存下平台原始資料
- **liaison/digest**：語意層，讀 channel 資料後賦予意義

### 主要資料表

**Identity 層**

| 表 | 說明 |
|----|------|
| `identity` | 跨 channel 的人或組織（`kind=personal/group`） |
| `identity_channel_participant` | identity 在各 channel 的帳號對應 |
| `property_type` | 屬性型別定義（`text`\|`enum`\|`date`\|`boolean`），含 `allow_multiple` 與 enum 合法值清單 |
| `identity_property` | identity 本身的屬性值（性別、住所、職稱…），含 `reviewable_id` |
| `identity_relation` | 兩個 identity 之間的有向關係，含 `reviewable_id` |
| `identity_relation_property` | 關係本身的屬性（角色、時間性、備註），含 `reviewable_id` |

**Reviewable 層**（推論來源與信效度評審）

| 表 | 說明 |
|----|------|
| `reviewable` | 任何可被評審的推論單元，記錄支撐推論的 `message_ids`（對應 `liaison.messages.id`） |
| `reviewable_review` | review agent 的評審紀錄，含信度、效度、reason、reviewed_by，支援軟刪除 |

**Event / Task 層**

| 表 | 說明 |
|----|------|
| `event` | 有意義的事件，含分類、優先級、摘要、時間戳 |
| `event_message` | event 與 channel 原始訊息的多對多 |
| `event_identity` | event 涉及哪些 identity 及其角色 |
| `task` | 由 event 衍生的待辦任務 |
| `task_log` | task 狀態變更日誌（當前狀態 = 最後一筆） |

完整 DDL 見 [`db/schema.sql`](./db/schema.sql)。

## API

Digest 提供一支輕量 REST API（FastAPI，預設 `:8002`），供外部服務查詢 identity 資訊。

### 啟動

```bash
cp .env.example .env   # 填入 DB_URL、LOGOS_IDENTITY_ID、API_PORT
uv sync
uv run uvicorn api:app --port 8002
```

### 端點

#### `GET /identity/me/participants`

回傳 `LOGOS_IDENTITY_ID`（`.env` 指定）在各 channel 的帳號。

```json
{
  "identity_id": "9f95c093-…",
  "participants": [
    { "channel": "line_personal", "external_id": "UYXq4h…" }
  ]
}
```

#### `GET /identity/{identity_id}/participants`

回傳任意 identity 在各 channel 的帳號。

| 狀態碼 | 說明 |
|--------|------|
| 200 | 成功，回傳 participant 清單 |
| 404 | identity 不存在或無 participant |
| 503 | `LOGOS_IDENTITY_ID` 未設定（`/me` 端點專屬） |

### 目前已建立的 Identity

| name | identity_id |
|------|-------------|
| 羅格致 | `9f95c093-f7ec-40eb-aad7-268dd0e843e9` |
| OPENLOHAS | `c20aaeb4-3100-4147-8625-72a3237c9473` |
| Josh | `9ad9530b-c0e4-49c6-a2f4-bf2ef9974037` |
| Mox | `08a34b60-966c-4e88-87ae-7e3d8114d068` |

## 結構

```
digest/
├── .agent/
│   └── rules/
│       ├── channel-scan.md      # 掃哪些 channel、哪些紀錄哪些忽略
│       ├── classification.md    # 訊息分類與評級依據
│       └── reporting.md         # 呈報 channel 與時機
├── db/
│   ├── schema.sql               # PostgreSQL DDL
│   └── setup.sh                 # 初始化腳本（建表）
├── api.py                       # FastAPI — identity / participant 查詢
├── pyproject.toml
├── .env                         # 實際路徑與設定（gitignored）
├── .env.example                 # 設定範本
├── README.md
└── AGENT_PLAN.md
```

## 設定方式

```bash
cp .env.example .env
# 填入 DB_URL、LOGOS_IDENTITY_ID、API_PORT 及各 channel 端點
```

初次建立資料庫：

```bash
sh db/setup.sh
```

詳細欄位說明見 `.env.example`。
