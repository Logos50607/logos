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

### LINE 個人帳號 inbound（已可用）

```bash
# 1. 啟動 Chrome（見 src/channels/line/personal/README.md）
# 2. 開始錄製
uv run src/channels/line/personal/capture.py --duration 60

# 3. 解析訊息
python3 src/processors/line_personal.py --input src/channels/line/personal/captured.json

# 4. 查看 operation type 統計（探索資料結構用）
python3 src/processors/line_personal.py --input src/channels/line/personal/captured.json --discover
```

## 實作原理 (Implementation Details)

採用 **Functional Core, Imperative Shell** 架構：

- **Channels**：各平台介接，只管收發，不含業務邏輯
- **Processors**：純函式，raw 訊息 → 統一 Message schema
- **Output**：任務輸出與 outbound 觸發
- **Core**：Pipeline 協調，依賴注入，不硬編碼 channel

架構決策與邊界定義見 `.agent/rules/architecture.md`。

## 模組實作狀態

| 模組 | 狀態 |
|------|------|
| LINE 個人 inbound（CDP capture） | ✅ |
| LINE 個人 outbound（CDP send） | ⬜ |
| LINE 官方 設定精靈（setup wizard） | ✅ `src/channels/line/official/setup.py` |
| LINE 官方 inbound（webhook） | ⬜ |
| LINE 官方 outbound（push/reply） | ⬜ |
| Processors（訊息解析） | ✅ LINE personal（`src/processors/line_personal.py`）|
| Output（任務輸出） | ⬜ |
| Core pipeline | ⬜ |
