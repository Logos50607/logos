---
name: ask-ruocosi
trigger: always_on
description: "當專案有需要 Logos 決定的事，主動推送給若可思，讓若可思在適當時機問 Logos。"
---

# 推送待決問題給若可思 (Ask Ruocosi)

## 核心規則

**專案不應被動等待 Logos 來讀 ASK_HUMAN.md。** 需要 Logos 決定的事，主動推送給若可思，由若可思透過 LINE 問他。

## 何時推送

- `ASK_HUMAN.md` 新增項目後，**若這件事需要 Logos 近期決定**，主動呼叫 CLI
- 不是每筆都推——純紀錄、長期擱置的問題不推
- 判斷標準：「Logos 現在不知道這件事，但他應該知道」

## 呼叫方式

```bash
# 單筆問題
direnv exec /data/logos/liaison/digest \
  uv run --directory /data/logos/liaison/digest ask.py \
  "問題內容" --project <專案名稱> --priority high

# 從 ASK_HUMAN.md 批次推送未勾選項目
direnv exec /data/logos/liaison/digest \
  uv run --directory /data/logos/liaison/digest ask.py \
  --file ASK_HUMAN.md --project <專案名稱>

# 緊急：立刻通知若可思
... ask.py "問題" --project <專案> --priority critical --alert
```

## Priority 選擇

| priority | 說明 |
|----------|------|
| `critical` | 需要立即決定，若可思馬上通知 |
| `high` | 今天內希望得到回應（預設） |
| `normal` | 近期決定即可，若可思等主動觸發時問 |

## 去重機制

同專案同問題 7 天內只推一次，重複呼叫自動跳過。

## 注意

- 推送後若可思會在**下次主動觸發時**用自己的語氣問 Logos，不會立刻發訊息（除非 `--alert`）
- Logos 回應後，記得在 `ASK_HUMAN.md` 勾選對應項目（`- [x]`）
- 若可思問完後，`event` 會由 Logos 或 AI 標記 resolved
