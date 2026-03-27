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
│   │       ├── personal/       # CDP tap LINE Chrome extension（個人帳號）
│   │       └── official/       # LINE Messaging API（官方帳號，webhook + push）
│   ├── processors/             # 訊息分析與任務提取
│   ├── output/                 # 任務清單與通知輸出
│   └── core/                   # 核心協調邏輯
├── README.md
├── AGENT_PLAN.md
├── ASK_HUMAN.md
└── DEPENDENCIES.md
```

## 使用指南 (Usage Guide)

> 待建立

## 實作原理 (Implementation Details)

採用 **Functional Core, Imperative Shell** 架構：

- **Channels**：各平台 read-only 介接，確保不觸碰未讀狀態
- **Processors**：純函式，負責訊息解析與任務提取
- **Output**：任務清單輸出（本地檔案、通知等）
- **Core**：協調 pipeline，注入依賴

## 專案初始化紀錄

- 初始化日期：2026-03-23
- 狀態：初始化中
