---
name: cloud-monitor
description: "雲端資源費用與用量監控：GCP billing、AI model token，異常時 LINE 通知。"
---

# Cloud Monitor — 雲端資源監控

## 背景與痛點

個人開發者，一個人管多個 GCP project，沒有公司財務支援。2026-03 曾因 Places API 被扣約 800 TWD 而不自知，事後才在帳單發現。核心痛點：

- 沒有主動通知，費用異常只能靠月底對帳單發現
- 多個 project 分散管理，沒有整體視野
- 部分 project 費用可向夥伴請款，需要分開追蹤

這個模組的目標是：**讓費用、用量、部署事件都能即時推到 LINE，不再有帳單驚喜。**

## 核心目標

監控所有對外付費的雲端資源，在費用異常或接近上限時主動通知，避免帳單驚喜。

## 監控範圍

| 子模組 | 資源 | 狀態 |
|--------|------|------|
| `gcp/` | GCP billing（所有 project） | **進行中** |
| `model-tokens/` | Anthropic、OpenAI 等 API 用量 | 藍圖 |

## 通知架構

```
費用/用量事件
    ↓
Cloud Function / 排程腳本
    ↓
LINE 通知（目前：LINE Notify 或 OA bot push）
```

目前使用 LINE OA bot（`liaison/switchboard` 管理），之後統一走 OA bot push message。

## 預算分類

部分專案費用可向夥伴請款，不計入個人額度。在各子模組的設定中以 `billable_to` 欄位標記：

```json
{
  "project": "trip-assistant-490916",
  "budget_twd": 100,
  "billable_to": "self"
}
```

```json
{
  "project": "some-partner-project",
  "budget_twd": 500,
  "billable_to": "partner-A"
}
```

## 關聯模組

- `registry/` — secrets 存取稽核，共用同一套 LINE 通知
- `liaison/switchboard` — LINE 訊息發送
