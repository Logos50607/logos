---
name: identity-observation
trigger: always_on
description: "對話中觀察到任何 identity（人或組織）的特質、關係、角色，必須即時寫入 digest DB，不得只留在 context 裡。"
---

# Identity 觀察即時寫入規範

## 核心規則

對話中每當得知任何 identity 的新資訊，**必須立即寫入 digest DB**，不得只停在記憶裡等之後補。

## 適用情境

| 觀察類型 | 寫入目標 |
|----------|----------|
| 本名、暱稱、生日、職稱… | `identity_property` |
| 個性、行為傾向、喜好 | `identity_property`（`note` type，可多筆） |
| 與他人的關係 | `identity_relation` + `identity_relation_property` |
| 隸屬公司、專案 | `identity_relation`（relation_type = `belongs_to`） |
| 公司、專案的定位 | `identity_property`（`note` type） |

## 寫入格式

```sql
-- 人物特質
INSERT INTO identity_property (identity_id, property_type_id, value)
SELECT '<uuid>', id, '<觀察內容>' FROM property_type WHERE name = 'note';

-- 隸屬關係
INSERT INTO identity_relation (from_identity_id, to_identity_id, relation_type)
VALUES ('<person_uuid>', '<org_uuid>', 'belongs_to');
```

## 不寫入的情境

- 推測成分高、尚未被本人或脈絡確認的資訊 → 先標注為推測再寫，或等確認後再寫
- 訊息 ID、原始 payload 等原始資料 → 屬於 liaison-channel，不在 digest

## DB 連線

```
postgresql://line:line@localhost:5433/digest
```
