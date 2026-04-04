---
name: cloud-monitor-model-tokens
description: "AI model API 用量監控藍圖：Anthropic、OpenAI 等，與 GCP billing 共用通知架構。"
---

# Model Token Monitor（藍圖）

## 核心目標

監控 AI model API 的 token 用量與費用，與 GCP billing 共用同一套通知機制。

## 監控對象（規劃）

| Provider | API | 計費單位 |
|----------|-----|---------|
| Anthropic | Claude API | input/output tokens |
| OpenAI | OpenAI API | tokens / requests |
| Google | Gemini API（`gen-lang-client-0013136576`） | tokens |

## 設計方向

### 用量查詢
各 provider 提供不同的 usage API：
- **Anthropic**：`/v1/usage`（需確認是否有 org-level usage endpoint）
- **OpenAI**：`/v1/usage`（有每日用量 endpoint）
- **Gemini**：透過 GCP billing export（同 `gcp/`）

### 通知整合
與 `gcp/` 共用同一個 Cloud Function 通知介面，統一格式：

```
[雲端監控] 2026-04-04
GCP: 45 TWD / 100 TWD (45%)
  trip-assistant: 40 TWD（Maps API）
  其他: 5 TWD
Anthropic: $2.3 / $5 (46%)
```

## 前置條件（實作前需確認）

- [ ] 確認 Anthropic API 有 usage 查詢 endpoint
- [ ] 整理各 provider 的 API key 存放位置（加入 `whitelist.json`）
- [ ] 決定 token budget 門檻（USD 或 token 數）
