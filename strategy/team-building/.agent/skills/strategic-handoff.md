---
name: strategic-handoff
description: "將策略規劃轉化為執行組可落地的 disciplines 並交付。當策略組完成某項規劃、需要交給執行組時使用。"
trigger: model_decision
---

# 策略交付

## 用途

將策略組的規劃成果轉化為目標執行組可直接使用的 disciplines，並在目標組建立或更新對應專案。

## 執行步驟

1. **盤點交付物**：
   - 列出本次規劃產出的所有 disciplines（rules / workflows / skills / templates）。
   - 逐項確認是否符合 `strategy-output-standard` rule。

2. **確認目標組與專案**：
   - 決定交付至哪個組、哪個專案（現有或新建）。
   - 若需新建專案：在目標組目錄下執行 git init + 建立 README / AGENT_PLAN / ASK_HUMAN / `.agent/` 結構。

3. **放置 disciplines**：
   - 將 rules 放入目標專案的 `.agent/rules/`。
   - 將 workflows 放入 `.agent/workflows/`。
   - 將 skills 放入 `.agent/skills/`。
   - 將 templates 放入 `templates/`。
   - 若有特定情境的執行紀錄（如某來源的評估結果），放入 `records/` 而非 `.agent/`。

4. **檢查跨組依賴**：
   - 依據 `dependency-first` rule，確認交付物中的跨組假設是否成立。
   - 缺口記入策略組 AGENT_PLAN.md。

5. **更新策略組待辦**：
   - 在策略組 AGENT_PLAN.md 標記該項規劃為已交付。
   - 新增後續追蹤項：「待使用者核可後，由 X 組依框架執行」。

6. **提交變更**：
   - 在目標組專案中執行 `/git-commit`。
   - 在策略組專案中執行 `/git-commit`。
