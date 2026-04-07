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
├── switchboard/    # 對外聯繫工具入口（LINE 個人 / 官方 symlink）
└── README.md       # 本文件
```

## 工具

### Switchboard

**需要對外聯繫，一律使用 [`switchboard/`](./switchboard/README.md)。**

Switchboard 是聯絡組的訊息工具入口，目前收錄：
- `line-personal/`：LINE 個人帳號（CDP + FastAPI :8000）
- `line-official/`：LINE 官方帳號（Playwright + FastAPI :8001）

兩者皆為 symlink，實體位於 `/data/personal/`。詳細啟動與使用方式見 `switchboard/README.md`。

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

| Channel | Inbound | Outbound | 說明 |
|---------|---------|----------|------|
| LINE 個人帳號 | ✅ | ✅ | CDP + FastAPI :8000；`line-personal/` |
| LINE 官方帳號 | ✅ | ✅ | Playwright + FastAPI :8001；`line-official/` |
| Discord | ⬜ | ⬜ | |
| Trello | ⬜ | ⬜ | |
