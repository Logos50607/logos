---
name: evaluate-permission-request
trigger: always_on
description: "監察組收到 permission request 時的評估與執行流程。"
---

# 權限請求評估流程

## 輸入格式

```
Permission request:
from: <組別>
working_dir: <路徑>
tool: <Write|Bash|...>
action: <說明>
original_prompt: <完整 prompt>
```

## 執行步驟

### 1. 解析請求

從輸入中提取：`from`、`working_dir`、`tool`、`action`、`original_prompt`

### 2. 對照 permission-policy 判斷

依 `permission-policy.md` 的規則順序：

- **Auto-deny** → 直接回傳拒絕原因，跳至步驟 5
- **Auto-approve** → 跳至步驟 3
- **Escalate** → 跳至步驟 4

### 3. 重執行（Auto-approve）

```sh
cd <working_dir> && claude --allowedTools "<tool>" -p "<original_prompt>"
```

將執行結果連同審核記錄一起回傳給呼叫方。

### 4. 轉人工（Escalate）

在 `/data/logos/supervision/permissions/` 的 `ASK_HUMAN.md` 新增：

```
- [ ] YYYY-MM-DD 待裁示：<from> 請求使用 <tool> 於 <working_dir>，理由：<action>
```

並通知聯絡組（若聯絡組回報統整已就位）。

### 5. 寫入稽核日誌

無論何種決定，追加至 `audit-log/YYYYMMDD.jsonl`：

```sh
echo '{"timestamp":"<ISO>","from":"<from>","working_dir":"<wd>","tool":"<tool>","action":"<action>","decision":"<approved|denied|escalated>","reason":"<reason>"}' \
  >> audit-log/$(date +%Y%m%d).jsonl
```

### 6. 回傳結果

- 允許：重執行結果
- 拒絕：拒絕原因
- 轉人工：告知已記錄，等待人工裁示
