---
name: switchboard-architecture
trigger: always_on
description: "Switchboard 架構決策紀錄：channel 設計原則、secrets 取用方式、inbound/outbound 邊界。"
---

# Switchboard 架構決策

## Channel 設計原則

每個 channel 是獨立的介接層，對外只暴露統一介面，不讓上層（processors/core）感知平台細節。

目前實作：

| Channel | 子類型 | Inbound | Outbound | 機制 |
|---------|--------|---------|----------|------|
| LINE 個人帳號 | `line/personal/` | ✅ CDP tap | ⬜ | Chrome extension service worker 攔截，不觸發 sendChatChecked |
| LINE 官方帳號 | `line/official/` | ⬜ | ⬜ | Messaging API webhook + push/reply |

### LINE 個人 vs 官方的取捨

| | 個人帳號 | 官方帳號 |
|--|---------|---------|
| 申請成本 | 無 | 需申請 Official Account |
| Inbound | CDP 攔截（非官方） | Webhook（官方 API） |
| Outbound | CDP inject JS（待建） | Push/Reply API |
| 訊息來源 | 人類個人帳號 | Bot 帳號（對方看到是機器人） |
| 適用場景 | 主人與 AI 的私人溝通 | 對外服務、多用戶通知 |

## Secrets 取用策略

不直接讀取路徑，一律透過以下介面取得：

- **本地（monorepo）**：`get-secret.sh <name> liaison/switchboard`
- **交付（standalone）**：env var（見 `.env.example`）

消費端使用 `deliver/skills/consume-monorepo-module` 中定義的雙模式 resolver。

目前已登記的 secrets（`internal-control/whitelist.json`）：
- `line-personal-session`：Chrome session 目錄
- `line-official-channel-secret`：Messaging API Channel Secret
- `line-official-channel-token`：Messaging API Access Token

## Pipeline 邊界

```
channels/     ← 平台介接，只管「收到什麼」「發出什麼」
processors/   ← 純函式，raw 訊息 → Message schema，不依賴任何 channel
output/       ← 任務輸出與 outbound 觸發，不依賴 channel 實作細節
core/         ← Pipeline 協調，注入依賴，不含業務邏輯
```

Processors 不得 import 任何 channel 模組。Core 透過依賴注入，不硬編碼 channel。

## 未讀狀態保護

LINE 個人帳號 inbound 的核心約束：**任何情況下不得觸發 `sendChatChecked`**。

違反方式（禁止）：
- 主動開啟 LINE UI 視窗（會觸發 sendChatChecked）
- 呼叫任何 LINE extension 的 mark-as-read API

例外：outbound send 本身屬於主動行為，開啟聊天室是預期行為。
