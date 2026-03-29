---
name: evaluate-permission-request
trigger: always_on
description: "監察組收到 permission request 時的評估與執行流程，涵蓋 bash、write、cross-team-p 三種類型。"
---

# 權限請求評估流程

## 輸入格式

```
Permission request:
from: <組別>
type: bash | write | cross-team-p
working_dir: <路徑>
request: <具體說明要做什麼>
original_prompt: <完整原始 prompt>
```

## 執行步驟

### 1. 解析請求

從輸入中提取：`from`、`type`、`working_dir`、`request`、`original_prompt`

### 2. 對照 permission-policy 判斷

依 `permission-policy.md` 的規則順序：

- **刪除操作**（request 含 rm / delete / 刪除 / mv to trash）→ 跳至步驟 3a
- **Auto-deny** → 直接回傳拒絕原因，跳至步驟 5
- **Auto-approve** → 依 type 跳至 3b / 3c / 3d
- **Escalate** → 跳至步驟 4

### 3a. Soft-delete（刪除備份）

```sh
BACKUP=/tmp/supervision-trash/$(date +%Y%m%d)
mkdir -p "$BACKUP"
mv <target_file> "$BACKUP/"
```

回報備份路徑，decision 記為 `soft-deleted`，跳至步驟 5。

### 3b. type: bash（執行指令）

監察組直接在自身工具權限內執行：

```sh
cd <working_dir> && <指令>
```

### 3c. type: write（寫入檔案）

監察組使用 Write 工具依 `original_prompt` 所描述的內容寫入目標路徑。

### 3d. type: cross-team-p（跨組呼叫）

監察組使用 Bash 工具，以最小必要 `--allowedTools` 呼叫目標組：

```sh
cd <target_working_dir> && claude --allowedTools "<最小必要工具>" -p "<original_prompt>"
```

將執行結果連同審核記錄一起回傳給呼叫方。

### 4. 轉人工（Escalate）

在 `/data/logos/supervision/command-permission-request/ASK_HUMAN.md` 新增：

```
- [ ] YYYY-MM-DD 待裁示：<from> 請求 <type> 於 <working_dir>，理由：<request>
```

並通知聯絡組（若聯絡組回報統整已就位）。

### 5. 寫入稽核日誌

無論何種決定，追加至 `audit-log/YYYYMMDD.jsonl`：

```sh
echo '{"timestamp":"<ISO>","from":"<from>","type":"<type>","working_dir":"<wd>","request":"<request>","decision":"<approved|denied|soft-deleted|escalated>","reason":"<reason>"}' \
  >> /data/logos/supervision/command-permission-request/audit-log/$(date +%Y%m%d).jsonl
```

### 6. 回傳結果

- 允許：執行結果
- 拒絕：拒絕原因
- 轉人工：告知已記錄，等待人工裁示
