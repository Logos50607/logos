---
name: delegate-to-education
description: "策略組將任務派給教育組的標準流程。目前因跨組任務派發機制尚未建立，由策略組暫時代勞；未來應由教育組自行接收並執行。"
trigger: model_decision
---

# 派任務給教育組

## 當前架構限制

**跨組任務派發機制尚未建立**：目前沒有 RemoteTrigger 或 `call-agent` 能讓策略組真正「發派後讓教育組自己跑」。

策略組的正確定位是**組織層，不是執行層**。不得自己執行教育組的工作（如讀 session、產出 discipline 草稿）。

## 判斷流程

```
收到「叫教育組做 X」的指令
    ↓
確認教育組是否有對應的 trigger / manifest / workflow
    ↓ 有 → 透過對應機制觸發（RemoteTrigger / manifest）
    ↓ 無 → 記錄架構缺口，暫時代勞並標注
```

## 有機制時：觸發教育組

1. 檢查 RemoteTrigger 清單：`RemoteTrigger list`
2. 若有對應 trigger → `RemoteTrigger run <trigger_id>`，附上任務說明
3. 若有 manifest → 確認 `operations/scheduling` 是否能立即觸發

## 無機制時：策略組暫時代勞

**必須標注代勞事實**，不得靜默執行。

1. 告知使用者：「教育組尚無接收機制，策略組暫時代勞，執行結果需人工移交」
2. 以 `/extract-disciplines` skill 執行萃取（按 skill 內定義的步驟走）
3. 將草稿存入 `education/knowledge-synthesis/reports/discipline-proposals/`
4. 在策略組 `AGENT_PLAN.md` 記錄架構缺口：

```
- [ ] <YYYY-MM-DD> 建立教育組任務接收機制（RemoteTrigger 或 call-agent）
      前置條件：通訊組 call-agent 封裝就緒
```

## 不得做的事

- 自己開 general-purpose agent 直接讀 session 並產出 discipline（跳過教育組）
- 呼叫 `/extract-disciplines` 後親自執行其中的技術步驟（這是教育組的工作）
- 假設教育組已有接收機制而未先確認
