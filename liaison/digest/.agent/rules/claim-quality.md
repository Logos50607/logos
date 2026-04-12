---
name: claim-quality
trigger: always_on
description: "寫入 identity_property/relation 前的品質規範：原子化、代詞解析、地點時間確認、agent 推論驗證。"
---

# Claim 品質規範

## 1. 原子化（Atomicity）

**每條 claim 只包含一個陳述。**

- 用句號結尾，不用分號串聯多個子句
- 禁止：「有一位哥哥，2026-01 來台探望；哥哥曾就讀 Chula」（三個事實）
- 正確：三條各自獨立的 note

複合事實必須拆分，各自建立獨立的 reviewable：

```
❌ "感情史：有 2 段正式交往，各約 2 年；另有 situationship"
✓  "有過 2 段正式交往關係"
✓  "每段關係各約 2 年"
✓  "最後一段帶有 situationship/love bombing 性質"
```

## 2. 代詞解析

含代詞（He/She/They/他/她/他們）的訊息，**必須先讀上下文確認指涉對象**，才能寫 claim。

```sql
-- 讀前後 2 分鐘的對話（±120000 ms）
WITH target AS (SELECT created_at, conversation_id FROM messages WHERE id = '<msg_id>')
SELECT m.id, p.external_id, m.text, to_timestamp(m.created_at/1000) as dt
FROM messages m
JOIN participants p ON p.id = m.sender_id
JOIN target t ON m.conversation_id = t.conversation_id
WHERE m.created_at BETWEEN t.created_at - 120000 AND t.created_at + 120000
ORDER BY m.created_at;
```

確認代詞指涉後，才能推論該事實屬於哪個 identity。

## 3. 地點與時間確認

涉及「去了哪裡」「誰來了」等地點 claim，**必須先確認當事人當時在哪裡**。

- 判斷方式：看訊息前後的地點線索（「到家了」「在機場」「今天飛回去」等）
- 「X 來這裡」的「這裡」取決於說話者當時的位置，不是預設的常駐地

## 4. 計劃 ≠ 事實

**已計劃但未確認發生的事，不得寫成既成事實。**

- 若訊息說「明天他要來」，要找後續確認（「他來了」「我們見面了」等）再寫入
- 若無後續確認，只能寫「計劃」或「提及想…」，不能寫「來了」

## 5. Agent 推論需抽樣驗證

使用 agent 分析訊息後產生的 claim，**寫入前須抽驗至少 2–3 條原始訊息脈絡**，確認推論正確。

抽驗重點：
- 代詞指涉是否正確
- 地點判斷是否有依據
- 時間點的前後文是否支持結論

## 6. 現有 compound notes 的處理

發現現有 compound note（value 中含分號或多個子句）時，應：
1. 拆分為多條原子 note
2. DELETE 原條，INSERT 各原子條（各自建 reviewable）
3. 不保留 compound 版本
