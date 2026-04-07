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

## 結構

```
digest/
├── .agent/
│   └── rules/
│       ├── channel-scan.md      # 掃哪些 channel、哪些紀錄哪些忽略
│       ├── classification.md    # 訊息分類與評級依據
│       └── reporting.md         # 呈報 channel 與時機
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
