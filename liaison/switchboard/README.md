---
name: switchboard
description: "AI 訊息整合閘道器，彙整多平台訊息並轉換為任務清單與提醒。"
---

# Switchboard

AI 驅動的訊息整合閘道器，協助使用者在不破壞原始訊息未讀狀態的前提下，彙整來自多平台的訊息，並轉換為可操作的任務清單與提醒。

## 核心目標 (Core Goal)

讓 AI Agent 在有邊界的狀況下：
1. 讀取各平台的訊息（LINE、Discord、Trello 等）
2. 分析並整合成結構化任務清單
3. 觸發後續動作或通知使用者
4. **不破壞原始訊息的未讀狀態**

## 結構索引 (Structure Index)

```
switchboard/
├── .agent/
│   ├── rules/          # 專案規範
│   ├── skills/         # 輔助技能
│   └── workflows/      # 自動化工作流
├── src/
│   ├── channels/               # 各平台 channel 介接層
│   │   └── line/
│   │       ├── personal/       # 薄 adapter，呼叫 /data/personal/line-personal API :8000
│   │       └── official/       # 薄 adapter，呼叫 /data/personal/line-official API（遷移中）
│   ├── processors/             # 訊息分析與任務提取
│   ├── output/                 # 任務清單與通知輸出
│   └── core/                   # 核心協調邏輯
├── README.md
├── AGENT_PLAN.md
├── ASK_HUMAN.md
└── DEPENDENCIES.md
```

### 外部服務（獨立部署，非本 repo）

| 服務 | 位置 | 說明 |
|------|------|------|
| line-personal | `/data/personal/line-personal/` | Chrome CDP + PostgreSQL + FastAPI :8000 |
| line-official | `/data/personal/line-official/` | Messaging API + webhook server（搬遷中） |

## 使用指南 (Usage Guide)

### LINE 個人帳號 inbound

LINE 個人帳號服務已獨立至 `/data/personal/line-personal/`（CDP + PostgreSQL + FastAPI）。

Switchboard 的 `src/channels/line/personal/` 為薄 adapter，透過 API 呼叫消費：

```bash
# 啟動 line-personal 服務（在 /data/personal/line-personal/）
bash scripts/ensure-services.sh   # sync daemon + media server

# Switchboard 透過 HTTP API 取得訊息
GET http://localhost:8000/messages
```

詳細操作見 `/data/personal/line-personal/README.md`。

## 實作原理 (Implementation Details)

採用 **Functional Core, Imperative Shell** 架構：

- **Channels**：各平台介接，只管收發，不含業務邏輯
- **Processors**：純函式，raw 訊息 → 統一 Message schema
- **Output**：任務輸出與 outbound 觸發
- **Core**：Pipeline 協調，依賴注入，不硬編碼 channel

架構決策與邊界定義見 `.agent/rules/architecture.md`。

## 模組實作狀態

| 模組 | 狀態 | 位置 |
|------|------|------|
| LINE 個人服務（CDP + DB + API） | ✅ 已獨立 | `/data/personal/line-personal/` |
| LINE 個人 channel adapter | ⬜ 待改寫為薄 adapter | `src/channels/line/personal/` |
| LINE 官方服務（setup + webhook + push） | 🔄 搬遷中 | → `/data/personal/line-official/` |
| LINE 官方 channel adapter | ⬜ | `src/channels/line/official/` |
| Processors（訊息解析） | ✅ LINE personal | `src/processors/line_personal.py` |
| Output（任務輸出） | ⬜ | |
| Core pipeline | ⬜ | |
