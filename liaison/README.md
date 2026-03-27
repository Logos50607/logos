---
name: liaison
description: "聯絡組總覽：AI 與人類的雙向通訊橋接，負責訊息接收、任務轉化與主動回報。"
---

# 聯絡組 (Liaison)

## 核心目標 (Core Goal)

作為 AI 團隊與人類之間的唯一通訊橋接層：

1. **Inbound**：接收人類透過各平台發出的訊息，轉化為 AI 可路由的任務
2. **Outbound**：彙整各組回報、警示、提醒，主動傳達給人類

## 結構索引 (Structure Index)

```
liaison/
├── switchboard/    # 訊息閘道（多平台 inbound / outbound 執行層）
└── README.md       # 本文件
```

## 工具

### Switchboard

[`switchboard/`](./switchboard/README.md) 是聯絡組的訊息執行工具，負責：
- 擷取各平台的人類訊息（inbound）
- 代 AI 團隊發送訊息給人類（outbound）

聯絡組不直接操作平台 API，一律透過 switchboard 的 channel 介面。

## 通訊策略

### 訊息流

```
人類 ──[任意平台]──→ switchboard inbound ──→ processor ──→ router ──→ 各組任務
各組回報 / 警示  ──→ switchboard outbound ──→ 人類
```

### 訊息優先級

| Priority | 說明 | 範例 |
|----------|------|------|
| `critical` | 立即發送 | 排程失敗、系統錯誤 |
| `daily` | 彙整至每日摘要 | 營運組日報 |
| `async` | 批次，人類空閒時處理 | 非緊急問題 |

## 與其他組別的介面

### 接收來源

| 組別 | 資料 | 時機 |
|------|------|------|
| 營運組 | `reports/YYYYMMDD/daily-summary.md` | 每日排程完成後 |
| 所有組 | escalate 訊息（`priority: critical`） | 任務失敗時 |

### 輸出目標

| 目標 | 格式 |
|------|------|
| 人類 | 自然語言摘要 / 問題（透過 switchboard） |
| 其他 AI 組別 | 結構化 `Message` 物件（JSON） |

## 目前 Channel 狀態

| Channel | Inbound | Outbound |
|---------|---------|----------|
| LINE (CDP) | ✅ `capture.py` 可用 | ⬜ 待建立 |
| Discord | ⬜ | ⬜ |
| Trello | ⬜ | ⬜ |
