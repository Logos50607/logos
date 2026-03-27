---
name: evaluate-source
description: "評估一個外部技能來源是否適合引入，產出引入紀錄。"
---

# /evaluate-source 工作流

對指定的外部技能來源進行初篩與深度評估，產出結構化的引入紀錄。

## 輸入

- 來源名稱與 URL（由使用者提供）

## 執行步驟

1. **取得來源資訊**：
   - 使用 `gh repo view <repo>` 或 web fetch 取得來源的 README、license、最近活動。
   - 列出來源中所有可識別的 skill/workflow 項目清單。

2. **初篩**：
   - 確認授權條款是否允許引用或 fork。
   - 確認最近 commit 日期，判斷是否仍在活躍維護（6 個月內有 commit 視為活躍）。
   - 閱讀來源的設計哲學說明，判斷是否與組織 discipline 體系方向相容。
   - **若初篩不通過**：在紀錄中註明理由，流程結束。

3. **盤點現有 discipline**：
   - 讀取目標 repo 的 `.agent/rules/`、`.agent/skills/`、`.agent/workflows/`，列出現有項目清單。
   - 此清單作為後續評估「互補性」的比對基準。

4. **逐項評估**：
   - 對來源中每個 skill/workflow，依以下五個維度評分並記錄：
     - **互補性**：與現有 discipline 是否功能重疊？重疊時是否仍有增量價值？
     - **獨立性**：可否獨立運作，或依賴來源中的其他元件？
     - **適配成本**：轉化為組織 discipline metadata 格式需要多少改動？（低/中/高）
     - **維護成本**：上游更新頻率與 adapter 同步難度？（低/中/高）
     - **優先級對齊**：該來源的優先級機制是否與組織體系衝突？
   - 將每個項目分為三類：「建議引入」「不需引入」「待觀察」。

5. **優先級衝突分析**：
   - 若來源自身定義了優先級體系（如 "user instructions > X > system prompt"），記錄其與組織 rules > skills 體系的對齊方式。

6. **產出引入紀錄**：
   - 複製 `templates/ADOPTION_RECORD.md` 至 `records/<source-name>.md`。
   - 填入所有評估結果。
   - 請示使用者核可評估結論。

## 產出

- `records/<source-name>.md`（已填寫的引入紀錄）
