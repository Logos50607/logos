---
name: adopt-skills
description: "將已核可的外部技能掛載至目標 repo 並撰寫 adapter。"
---

# /adopt-skills 工作流

依據已核可的引入紀錄，將外部技能實際掛載至目標 repo 並建立 adapter。

## 前置條件

- 已完成 `/evaluate-source`，且引入紀錄已獲使用者核可。
- 使用者已指定目標 repo（將掛載 `_vendor/` 的位置）。

## 執行步驟

1. **確認引入紀錄**：
   - 讀取 `records/<source-name>.md`，取得「建議引入」的項目清單。
   - 若紀錄中無「建議引入」項目，提示使用者並結束。

2. **建立 `_vendor/` 掛載**：
   - 切換至目標 repo 根目錄。
   - 若 `.agent/skills/_vendor/` 不存在，建立之。
   - 選擇掛載方式（預設 `git submodule`）：
     ```bash
     cd <target-repo>
     git submodule add <source-url> .agent/skills/_vendor/<source-name>
     ```
   - 若使用者指定其他方式（subtree 等），依指示執行。

3. **逐項撰寫 adapter**：
   - 對每個「建議引入」的 skill，在 `.agent/skills/<skill-name>/` 下建立 `SKILL.md`。
   - adapter 必須包含：
     - 符合 discipline metadata 格式的 YAML frontmatter（`name`, `description`, `trigger`）。
     - 引用 `_vendor/<source-name>/` 下對應原始檔案的路徑說明。
     - 本地化調整區塊（措辭修正、與現有 discipline 的銜接說明）。
   - adapter 範例結構：
     ```markdown
     ---
     name: <skill-name>
     description: "<一行描述>"
     trigger: model_decision
     ---
     # <Skill 名稱>

     > 原始來源：`.agent/skills/_vendor/<source-name>/<path>`

     （此處為本地化後的技能內容，引用並調整原始 skill 的指引）
     ```

4. **驗證 sync 相容性**：
   - 執行目標 repo 的 `/sync-disciplines` 或對應的同步機制。
   - 確認 adapter 被正確識別為標準 skill。
   - 確認 `_vendor/` 內容未被意外同步至其他位置。

5. **更新引入紀錄**：
   - 回到 `records/<source-name>.md`，勾選「執行狀態」中的對應項目。

6. **提交變更**：
   - 在目標 repo 中執行 `/git-commit`。

## 產出

- 目標 repo 中新增的 `_vendor/` submodule 與 adapter 檔案。
- 更新後的引入紀錄。
