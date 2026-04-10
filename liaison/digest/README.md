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

| 表 | 說明 |
|----|------|
| `identity` | 跨 channel 的真實人物 |
| `identity_channel_participant` | identity 在各 channel 的帳號對應 |
| `identity_relation` | 兩個 identity 之間的有向關係 |
| `identity_group` / `identity_group_member` | 自定義分群（VIP 客戶、家人…） |
| `event` | 有意義的事件，含分類、優先級、摘要、時間戳 |
| `event_message` | event 與 channel 原始訊息的多對多 |
| `event_identity` | event 涉及哪些 identity 及其角色 |
| `task` | 由 event 衍生的待辦任務 |
| `task_log` | task 狀態變更日誌（當前狀態 = 最後一筆） |

完整 DDL 見 [`db/schema.sql`](./db/schema.sql)。

## 結構

```
digest/
├── .agent/
│   └── rules/
│       ├── channel-scan.md      # 掃哪些 channel、哪些紀錄哪些忽略
│       ├── classification.md    # 訊息分類與評級依據
│       └── reporting.md         # 呈報 channel 與時機
├── db/
│   └── schema.sql               # PostgreSQL DDL
├── .env                         # 實際路徑與設定（gitignored）
├── .env.example                 # 設定範本
├── README.md
└── AGENT_PLAN.md
```

## 設定方式

複製 `.env.example` 為 `.env`，填入各 channel 的 API 端點與呈報目標：

```bash
cp .env.example .env
# 編輯 .env，填入實際值
```

詳細欄位說明見 `.env.example`。
