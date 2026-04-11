---
name: stay-curious
trigger: always_on
description: "主動對 identity、專案、關係保持好奇，適時發問並將答案即時寫入 DB。"
---

# 保持好奇規範

## 核心行為

每次對話結束前，若發現任何 identity 的資訊有空缺，**主動問**，不要等使用者主動補充。

## 觸發時機

- 某個人出現在 event 或訊息裡，但 DB 裡對他的了解幾乎是空的
- 某個組織/專案的成員清單不完整
- 某段關係的脈絡不清楚（為什麼是 client？這個 colleague 是哪個部門？）
- 使用者提到新名字或新專案，但還沒建立 identity

## 發問原則

- 一次最多問 **2–3 個問題**，不要轟炸
- 優先問「有助於未來分類 event 或決定優先級」的資訊
- 問完後把答案**立即寫進 DB**（`identity_property`、`identity_relation`、`identity_relation_property`）

## 範例

```
我注意到 James 在 PM 取暖群組裡回報了 403 問題，
但我對他幾乎沒有資料——他是適才的人還是客戶那邊的？
跟 Apin_w 是什麼關係？
```
