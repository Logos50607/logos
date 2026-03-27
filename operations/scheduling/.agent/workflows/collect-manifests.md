---
name: collect-manifests
description: "掃描所有專案目錄，收集排程 manifest 並建立 registry 索引。由 daily-dispatch 每日觸發，亦可手動執行。"
---

# 收集排程 Manifest

## 用途

定期掃描組織目錄，發現新增、修改、移除的排程 manifest，更新 registry 索引。

## 前置條件

- `$LOGOS_ROOT` 環境變數已設定（預設 `/data/logos`）
- 各專案的 manifest 放置於 `.agent/schedules/*.manifest.md`

## 執行步驟

### 1. 掃描目標目錄

遍歷 `$LOGOS_ROOT` 下所有專案，搜尋符合路徑模式的檔案：

```
$LOGOS_ROOT/**/.agent/schedules/*.manifest.md
```

記錄每個 manifest 的：
- 完整路徑
- 檔案修改時間
- YAML frontmatter 內容

### 2. 驗證格式

逐一檢查每個 manifest：

- **必填欄位**：`task_name`, `description`, `owner_group`, `owner_project`, `schedule.type`, `schedule.expr`, `command.type`, `command.working_dir`
- **條件欄位**：`command.type=script` 時 `script_path` 必填；`command.type=ai-evaluate` 時 `prompt_path` 必填
- **task_name 唯一性**：不可與其他 manifest 重複
- **schedule.expr 語法**：依 `schedule.type` 驗證表達式格式
- **command.working_dir**：目錄必須存在

不合規的 manifest → 記入 `registry/invalid.md`，附上錯誤說明。

### 3. 比對差異

與現有 `registry/index.md` 內容比對，識別：

- **新增**：manifest 存在但 registry 中無對應紀錄
- **修改**：manifest 的修改時間或內容與 registry 紀錄不同
- **移除**：registry 中有紀錄但 manifest 已不存在

產出差異摘要，記入本次收集報告。

### 4. 更新 registry

- **`registry/index.md`**：所有有效任務的索引表

  ```markdown
  | task_name | owner_group | schedule | command_type | enabled | last_status |
  ```

- **`registry/invalid.md`**：不合規的 manifest 清單

  ```markdown
  | 檔案路徑 | 錯誤原因 | 發現日期 |
  ```

- **`registry/<task_name>.md`**：各任務的 manifest 複本，附加：
  - 來源路徑
  - 收集時間
  - 最近執行狀態（從 reports/ 讀取）
  - 評估備註（見步驟 5）

### 5. AI 評估（僅差異存在時）

若有新增或修改的任務，評估以下項目：

- 排程頻率是否合理（例如不建議每分鐘執行的任務）
- 是否與現有任務的排程時間衝突（同一時段密度過高）
- 資源需求是否可承受

評估結果寫入對應的 `registry/<task_name>.md` 的「評估備註」區段。
若評估發現嚴重問題，將任務的 `enabled` 標記為 `false` 並記入 `ASK_HUMAN.md`。

### 6. 提交變更

執行 `/git-commit`。

## 建議執行頻率

每日一次（由 `daily-dispatch` 的第一步觸發），或手動執行以即時收集。
