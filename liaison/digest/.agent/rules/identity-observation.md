---
name: identity-observation
trigger: always_on
description: "對話中觀察到任何 identity（人或組織）的特質、關係、角色，必須即時寫入 digest DB，不得只留在 context 裡。"
---

# Identity 觀察即時寫入規範

## 核心規則

對話中每當得知任何 identity 的新資訊，**必須立即寫入 digest DB**，不得只停在記憶裡等之後補。

**Logos 本人也是觀察對象。** 分析任何人的對話時，若從中發現與 Logos 有關的事實（他說的話透露的特質、他的處境、他描述自己的方式），同樣要寫入他的 `identity_property`，而不只是更新對方的資料。使用者直接告知的事實（如婚姻日期、出身地）亦同。

## Property vs Relation vs Relation Property

**`identity_property`** = 這個人**本身**的屬性，拿掉所有關係之後還成立的事實
- 性別、名字、生日、住哪、職業、電話、興趣、性癖、性向、綽號
- 判斷標準：即使不認識 Logos，這件事對這個人還成立嗎？→ 成立則放 property

**`identity_relation`** = 兩個 identity 之間的**連結**，必須有兩端才存在
- 朋友、同事、戀人、屬於某組織

**`identity_relation_property`** = 這段**連結本身**的屬性，描述關係的性質、脈絡、動態
- 在這段關係裡的角色（PM、BD）
- 這段關係是現在還是過去（current / past）
- 這段關係的備註：怎麼認識、互動性質、發生過什麼事

**判斷方式**：把這個人從所有關係中抽離，資訊還成立嗎？
- 成立 → `identity_property`（例：某人住台南、綽號「阿海」、喜歡爬山）
- 不成立 → `identity_relation_property`（例：兩人是透過朋友介紹認識、合作關係已結束）

## 適用情境

| 觀察類型 | 寫入目標 |
|----------|----------|
| 本名、暱稱、生日、職稱、住所、性別、性向… | `identity_property` |
| 個性、行為傾向、喜好、身體特徵 | `identity_property`（`note` 或對應 type） |
| 與他人的關係 | `identity_relation` |
| 關係的性質、脈絡、互動動態 | `identity_relation_property`（`note` type） |
| 在某段關係中的角色 | `identity_relation_property`（`role` type） |
| 隸屬公司、專案 | `identity_relation`（relation_type = `belongs_to`） |
| 公司、專案的定位 | `identity_property`（`note` type） |

## 誰是合法的訊息來源

`reviewable.message_ids` 可以引用兩種 sender 的訊息，兩者都是有效來源：

| Sender | channel | sender_external_id | 說明 |
|--------|---------|-------------------|------|
| 使用者（Logos） | `claude-code-session` | `logos` | 直接告知的事實、糾正、補充 |
| AI agent（本 agent） | `claude-code-session` | `claude-code` | 從對話或 channel 資料做的推論，推論過程需寫清楚 |

**AI agent 必須把推論過程寫成訊息存入 channel，才能作為 reviewable 的來源。**

推論訊息的格式（`text` 欄位）：

```
[推論] identity: <name>，property: <type>=<value>
依據：從 <channel> 對話 <conv_external_id> 中，<具體觀察>，推論出 <結論>。
```

或對話推論：

```
[推論] identity: <name> 與 <name2>，relation: <type>
依據：<具體訊息內容或行為模式>，推論兩者為 <relation>。
```

## 寫入流程

每筆 claim 寫入步驟：

1. **POST 推論訊息至 channel**（若來源是 AI 推論）

```
POST http://localhost:8080/messages
{
  "channel": "claude-code-session",
  "conversation_external_id": "<session_id>",
  "sender_external_id": "claude-code",
  "sender_name": "Claude",
  "content_type": "text",
  "text": "[推論] ...",
  "created_at": <now_ms>,
  "external_id": "<本 agent 自訂的唯一 id>"
}
→ 回傳 message_id
```

2. **建立 reviewable**

```sql
INSERT INTO reviewable (message_ids)
VALUES (ARRAY['<message_id>'::uuid, ...])
RETURNING id INTO rv_id;
```

3. **寫入 claim**

```sql
INSERT INTO identity_property (identity_id, property_type_id, value, reviewable_id)
SELECT '<identity_uuid>', id, '<值>', rv_id FROM property_type WHERE name = '<type>';
```

## Reviewable 規範

- `reviewable.message_ids`：**不允許空陣列**，每筆 claim 必須有至少一則來源訊息
- 來源可混合：使用者訊息 + AI 推論訊息皆可放入同一 `message_ids`
- 信效度與原子性評分由獨立 review agent 執行，本 agent 不自評
- `reviewable_review.reason` 為必填；`atomicity` 低分時須在 reason 中說明建議如何拆分

## 不寫入的情境

- 推測成分高、尚未被本人或脈絡確認的資訊 → 先標注為推測再寫，或等確認後再寫
- 訊息 ID、原始 payload 等原始資料 → 屬於 liaison-channel，不在 digest

## DB 連線

```
postgresql://liaison:P7I-B4rS_qIemR0T1Fwsgc1xNoxhdIAM@localhost:5433/digest
```
