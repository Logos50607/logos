---
name: channel-scan
trigger: always_on
description: "定義 digest 掃描 channel 的規則：哪些來源要掃、哪些訊息要紀錄、哪些可忽略。"
---

# Channel 掃描規則

## 來源宣告

所有 channel 來源由 `.env` 宣告，**不得在程式碼或 discipline 中 hardcode 路徑或端點**。

每個 channel 須提供：
- API 端點（`*_API`）或本地資料路徑（`*_DATA`）
- 端點留空 → 自動跳過該 channel，不視為錯誤

## 掃描對象

| 欄位 | 說明 |
|------|------|
| `SCAN_INTERVAL_MINUTES` | 定期掃描間隔 |
| `LOOKBACK_MINUTES` | 每次回溯的時間視窗 |

掃描應為**冪等操作**：同一訊息被掃描兩次，不得產生重複的摘要條目。建議以訊息 ID + timestamp 去重。

## 紀錄 vs 忽略

以下情況**忽略**，不進入分類流程：

- 自己（bot / AI）發出的訊息
- 系統通知（`sender_type = system`）
- 已在上次摘要中處理過的訊息（重複掃到）

以下情況**必須紀錄**：

- 人類用戶發出的任何文字訊息
- 含附件（圖片、檔案、影片）的訊息 → 紀錄為「含媒體」，不需下載原始檔
- 轉發訊息 → 標記來源

## Channel 不可用時的處理

若某 channel API 無回應或回傳錯誤：
- 記錄警告，**不中斷**其他 channel 的掃描
- 該 channel 本輪跳過，下輪重試
- 連續 3 輪失敗 → 提升為 `critical` 事件，立即呈報
