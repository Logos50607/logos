---
name: identity-observation
trigger: always_on
description: "對話中觀察到任何 identity（人或組織）的特質、關係、角色，必須即時寫入 digest DB，不得只留在 context 裡。"
---

# Identity 觀察即時寫入規範

## 核心規則

對話中每當得知任何 identity 的新資訊，**必須立即寫入 digest DB**，不得只停在記憶裡等之後補。

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

## 寫入格式

每筆 claim（property / relation / relation_property）寫入時，**必須同步建立 `reviewable` 並填入 `reviewable_id`**。沒有 reviewable 的 claim 無法被 agent 評審。

```sql
-- 1. 建立 reviewable（來源訊息 UUID 陣列，對應 liaison.messages.id）
INSERT INTO reviewable (message_ids)
VALUES (ARRAY['<msg_uuid_1>'::uuid, '<msg_uuid_2>'::uuid])
RETURNING id INTO rv_id;

-- 2. 寫入 claim，帶入 reviewable_id
INSERT INTO identity_property (identity_id, property_type_id, value, reviewable_id)
SELECT '<identity_uuid>', id, '<觀察內容>', rv_id FROM property_type WHERE name = 'note';

-- 隸屬關係
INSERT INTO reviewable (message_ids) VALUES (ARRAY['<msg_uuid>'::uuid]) RETURNING id INTO rv_id;
INSERT INTO identity_relation (from_identity_id, to_identity_id, relation_type, reviewable_id)
VALUES ('<person_uuid>', '<org_uuid>', 'belongs_to', rv_id);
```

## Reviewable 規範

- `reviewable.message_ids`：支撐此推論的訊息 UUID 陣列（`liaison.messages.id`），**不允許空陣列**
- 信效度評分由獨立 review agent 執行，寫入 `reviewable_review`，本 agent 不自評
- `reviewable_review.reason` 為必填：評審 agent 須說明評分依據

## 不寫入的情境

- 推測成分高、尚未被本人或脈絡確認的資訊 → 先標注為推測再寫，或等確認後再寫
- 訊息 ID、原始 payload 等原始資料 → 屬於 liaison-channel，不在 digest

## DB 連線

```
postgresql://liaison:P7I-B4rS_qIemR0T1Fwsgc1xNoxhdIAM@localhost:5433/digest
```
