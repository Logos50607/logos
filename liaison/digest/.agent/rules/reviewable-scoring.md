---
name: reviewable-scoring
trigger: always_on
description: "reviewable_review 三個評分維度的定義與評分標準，供 review agent 執行評審時參照。"
---

# Reviewable 評審評分規範

## 前提

review agent 讀取 `reviewable`（推論單元）及其 `message_ids` 所指向的訊息原文，
對該推論填寫 `reviewable_review`，包含三個維度與必填的 `reason`。

```sql
INSERT INTO reviewable_review (reviewable_id, reliability, validity, atomicity, reason, reviewed_by)
VALUES ('<rv_id>', <1-5>, <1-5>, <1-5>, '<reason>', '<agent_name>');
```

---

## 三個評分維度

### 1. `reliability`（信度）1–5

**問題：這組 message 給定後，能否合理推論出這個 claim？**

評的是「推論品質」——從證據到結論的邏輯是否成立。

| 分數 | 標準 |
|------|------|
| 5 | 訊息直接陳述，無需推論（如本人自述「我住台南」） |
| 4 | 訊息強烈暗示，推論幾乎無疑義 |
| 3 | 訊息支持推論，但也存在其他合理解釋 |
| 2 | 訊息與推論有關，但關聯薄弱或有相反證據 |
| 1 | 訊息無法支撐此推論，推論站不住腳 |

### 2. `validity`（效度）1–5

**問題：讀過更多 context 後，這組 message 是否是正確的取樣？**

評的是「取樣品質」——當初引用的訊息有沒有代表性、有沒有遺漏關鍵訊息、有沒有引用不相關訊息。

| 分數 | 標準 |
|------|------|
| 5 | 引用的訊息是最直接的證據，沒有遺漏更好的來源 |
| 4 | 取樣合理，或許有更好的訊息但差異不大 |
| 3 | 取樣部分準確，有遺漏或有不相關訊息混入 |
| 2 | 取樣有明顯問題：漏掉關鍵反例，或引用錯誤對話 |
| 1 | 取樣完全錯誤：引用的訊息與此 claim 無關 |

### 3. `atomicity`（原子性）1–5

**問題：這筆 claim 是否描述一個單一事實？**

評的是「粒度品質」——claim 的 value 是否包含多個應該獨立存放的事實。

| 分數 | 標準 |
|------|------|
| 5 | 完全原子：一個事實、一個欄位（如 `gender=male`） |
| 4 | 大致原子，有輕微複合但不影響查詢 |
| 3 | 部分複合：value 含 2–3 個可獨立的事實 |
| 2 | 明顯複合：value 含多個事實，應拆分 |
| 1 | 嚴重複合：value 是一段敘述，包含大量不同維度的事實 |

**`atomicity` 低於 3 時，`reason` 必須說明建議的拆分方式。**

---

## `reason` 格式建議

`reason` 為必填，建議包含：
1. 各維度分數的簡要說明
2. 若 `atomicity < 3`：具體建議如何拆分（拆成哪幾筆、各自的 property_type 和 value）

範例：

```
reliability=4：訊息直接說「Logos 叫他弟弟」，稱謂清楚但仍需推論情感深度。
validity=3：引用訊息能佐證情感，但漏掉了表白那則更關鍵的訊息。
atomicity=2：value 同時包含「稱謂習慣」和「情感強度」，建議拆成：
  - note="對方稱 Logos 哥哥，Logos 稱對方弟弟"
  - note="Logos 對此人情感強烈（'I always love too hard'）"
```

---

## 評審對象的查詢

```sql
-- 找所有尚未被評審的 reviewable（無任何有效 review）
SELECT r.id, r.message_ids, r.created_at
FROM reviewable r
WHERE NOT EXISTS (
    SELECT 1 FROM reviewable_review rr
    WHERE rr.reviewable_id = r.id AND rr.deleted_at IS NULL
)
ORDER BY r.created_at;
```
