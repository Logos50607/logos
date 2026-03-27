---
name: maintain-vendor
description: "檢查已掛載的外部來源是否需要更新、退場或內化。含可排程的腳本與 claude -p 評估。"
---

# /maintain-vendor 工作流

定期檢查已掛載的 `_vendor/` 外部來源狀態，決定更新、退場或內化。

## 架構

本工作流分為兩層：

1. **腳本層**（`scripts/maintain-vendor.sh`）：執行機械性 git 操作，蒐集狀態資料，輸出結構化報告。
2. **評估層**：腳本透過 `claude -p` 將報告餵給 AI，由 AI 依據決策邏輯判斷處置方式並執行。

```
cron (營運組註冊)
  → scripts/maintain-vendor.sh <target-repo>
    → git fetch / diff / log（蒐集狀態）
    → 產出 JSON 狀態報告
    → claude -p "依據報告與決策邏輯，判斷處置方式並執行"
      → 更新 / 退場 / 內化 / 維持現狀
      → 更新 records/ 紀錄
      → /git-commit
```

完成後須至營運組註冊排程觸發（建議每季一次）。

## 腳本層：scripts/maintain-vendor.sh

### 輸入

```bash
./scripts/maintain-vendor.sh <target-repo-path>
```

### 腳本職責

1. **盤點已掛載來源**：
   ```bash
   cd "$TARGET_REPO"
   git submodule status .agent/skills/_vendor/*
   ```
   - 解析每個 submodule 的 commit hash 與來源名稱。

2. **逐一 fetch 上游**：
   ```bash
   for vendor_dir in .agent/skills/_vendor/*/; do
     source_name=$(basename "$vendor_dir")
     cd "$vendor_dir"
     git fetch origin

     local_head=$(git rev-parse HEAD)
     remote_head=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master)
     last_commit_date=$(git log -1 --format=%ci "$remote_head")
     days_since=$(( ($(date +%s) - $(date -d "$last_commit_date" +%s)) / 86400 ))
     behind_count=$(git rev-list --count HEAD.."$remote_head")
     changed_files=$(git diff --name-only HEAD.."$remote_head")

     cd "$TARGET_REPO"
   done
   ```

3. **蒐集 adapter 引用狀態**：
   ```bash
   # 該來源是否仍被引用（排除 _vendor 自身）
   references=$(grep -rl "$source_name" .agent/rules/ .agent/skills/ .agent/workflows/ \
     --include="*.md" | grep -v "_vendor/" || true)
   ```

4. **蒐集 adapter 偏離度**：
   ```bash
   # 對每個 adapter，計算與原始 skill 的差異比例
   for adapter in .agent/skills/*/SKILL.md; do
     skill_name=$(basename "$(dirname "$adapter")")
     # 找到對應的 vendor 原始檔（需從 adapter 中解析引用路徑）
     original_path=$(grep -oP '(?<=_vendor/)[^\s`]+' "$adapter" | head -1)
     if [ -n "$original_path" ]; then
       total_lines=$(wc -l < "$adapter")
       diff_lines=$(diff "$adapter" ".agent/skills/_vendor/$original_path" | grep -c "^[<>]" || true)
       divergence_pct=$(( diff_lines * 100 / total_lines ))
     fi
   done
   ```

5. **輸出 JSON 狀態報告**至 stdout：
   ```json
   {
     "target_repo": "<path>",
     "check_date": "YYYY-MM-DD",
     "sources": [
       {
         "name": "<source-name>",
         "local_head": "<hash>",
         "remote_head": "<hash>",
         "has_update": true,
         "last_commit_date": "YYYY-MM-DD",
         "days_since_last_commit": 45,
         "behind_count": 3,
         "changed_files": ["path/a.md", "path/b.md"],
         "is_referenced": true,
         "adapters": [
           {
             "skill_name": "<name>",
             "divergence_pct": 30,
             "affected_by_update": true
           }
         ]
       }
     ]
   }
   ```

## 評估層：claude -p 決策

腳本蒐集完狀態報告後，透過 `claude -p` 觸發 AI 評估：

```bash
report=$(cat /tmp/maintain-vendor-report.json)

claude -p "你是教育組的 skill 維護 agent。
以下是 _vendor/ 的狀態報告：

$report

請依據以下決策邏輯，對每個來源判斷處置方式，並執行對應操作。

## 決策邏輯（依序檢查，命中即停）

### 退場（任一成立）
- days_since_last_commit > 365
- is_referenced = false

### 內化（任一 adapter 成立）
- divergence_pct > 50

### 更新（has_update = true）
- affected_by_update = true → 更新 submodule 並調整 adapter
- affected_by_update = false → 更新 submodule，adapter 不動

### 維持現狀
- 以上皆不成立

## 執行操作

### 更新
1. cd <target-repo>/.agent/skills/_vendor/<source-name>
2. git checkout <remote_head>
3. cd <target-repo> && git add .agent/skills/_vendor/<source-name>
4. 若 affected_by_update = true，讀取受影響的 adapter 與更新後的原始 skill，調整 adapter 內容使其對齊
5. /git-commit

### 退場
1. cd <target-repo>
2. git submodule deinit -f .agent/skills/_vendor/<source-name>
3. git rm -f .agent/skills/_vendor/<source-name>
4. rm -rf .git/modules/.agent/skills/_vendor/<source-name>
5. 移除該來源對應的所有 adapter 目錄：git rm -rf .agent/skills/<skill-name>/
6. /git-commit

### 內化
1. 編輯 adapter：移除「原始來源」引用行與 _vendor 路徑引用
2. 確認 adapter 內容完全自足
3. 若該來源所有 adapter 都已內化，執行退場操作移除 submodule
4. /git-commit

## 紀錄更新
在 records/<source-name>.md 末尾追加：
### YYYY-MM-DD
- 處置：（更新 / 退場 / 內化 / 維持現狀）
- 上游版本：<commit-hash>
- 說明：（具體描述）

## 重要
- 每項處置前先列出判斷依據與預計操作，請示使用者核可後再執行。
- 若判斷有模糊地帶（如 divergence_pct 接近 50%），將疑慮寫入 ASK_HUMAN.md。"
```

## 排程註冊

腳本完成後，須至**營運組**註冊定期排程：

- 建議頻率：每季一次
- 觸發方式：由營運組的排程機制呼叫 `scripts/maintain-vendor.sh`
- 需提供營運組的資訊：腳本路徑、目標 repo 清單、排程頻率

## 實作歸屬

| 項目 | 負責組 |
|------|--------|
| `scripts/maintain-vendor.sh` 撰寫與測試 | 教育組 |
| 排程註冊與監控 | 營運組 |
| 決策邏輯調整（閾值等） | 教育組，重大變更需策略組核可 |
