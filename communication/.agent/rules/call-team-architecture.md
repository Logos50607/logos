---
name: call-team-architecture
trigger: always_on
description: "通訊組核心架構：跨組 -p 呼叫的 registry、任務分級與審核規則。"
---

# 跨組呼叫架構

## 核心原則

- **所有跨組 -p 呼叫必須經由通訊組**，不得由發起組直接呼叫目標組
- **所有任務必須預先註冊**於 `registry/`，未登記的任務一律拒絕執行
- **通訊組只管傳遞**（transport），不執行任務內容本身

## 任務 Registry

每個可呼叫的任務在 `registry/<team>/<task-id>.md` 中聲明：

```yaml
id: <team>.<task-id>          # 唯一識別，格式：目標組.任務名
target: <team>                # 目標組名稱
cwd: /data/logos/<team>/...   # 目標組執行目錄（-p 的 cwd）
provider: claude              # 預設 provider（claude / gemini / gemini-web）
mode: fire | reply            # fire=不等回應，reply=等結果
risk: low | medium | high     # 決定是否需要監察組審核
review: skip | required       # 覆寫 risk 預設行為（可選）
description: "..."            # 任務用途說明
```

## 任務分級與審核

| risk | 說明 | 審核 |
|------|------|------|
| `low` | 固定腳本，輸出可預期 | 自動放行 |
| `medium` | 創作類、輸出不確定 | 送監察組審核 |
| `high` | 涉及系統修改、刪除、設定變更 | 送監察組審核 |

`review: skip` 可強制跳過審核（僅限 low risk）。

## 呼叫模式

### Fire-and-forget
送出後不等回應，適用於非同步任務（如萃取 discipline、生成摘要）。

### Request-reply
送出後等回應才繼續，需搭配 `request_id`。
`request_id` 由通訊組在執行時生成（發起組不感知）。

## Provider 選擇

通訊組依下列優先順序選擇可用 provider：
1. 任務 registry 指定的 `provider`
2. 若該 provider quota 耗盡 → 依序 fallback：claude → gemini → gemini-web
3. quota 狀態由內控組提供查詢介面（`internal-control/quota-check`）

## 工具存取範圍（--allowedTools）

通訊組組出 `-p` 指令時，依下列原則限縮工具範圍：

```yaml
allowed_read:  <target_cwd>/**          # 只讀目標組自己的資料夾
allowed_write:
  - <target_cwd>/.agent/**
  - <target_cwd>/AGENT_PLAN.md
  - <target_cwd>/ASK_HUMAN.md
```

**例外**：若任務需要讀取其他組的資料，必須在 registry 條目中明確聲明額外的 `extra_read` 路徑，並標注原因。不得預設給予 monorepo 全讀權限。

Registry 條目中可加入：

```yaml
extra_read:
  - /data/logos/<other-team>/<project>/**   # 需要讀取的額外路徑，附理由
```

## 各組必要配合

每個目標組必須在自身 `.agent/workflows/` 下提供 `receive-task.md`，作為被 `-p` 喚醒時的入口。
