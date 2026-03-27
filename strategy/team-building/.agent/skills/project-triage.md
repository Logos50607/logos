---
name: project-triage
description: "評估一個專案的歸屬組別、是否需要拆解、或應封存。用於審閱待分類 repo 時。"
trigger: model_decision
---

# 專案分類與拆解評估

## 用途

對一個尚未分類的專案進行審閱，決定其歸屬組別、是否需要拆解為多個專案、或應封存。

## 執行步驟

1. **讀取專案內容**：
   - 讀取 README.md（若有）。
   - 讀取目錄結構（`ls -R` 或 `tree`，深度 2 層）。
   - 讀取最近 10 筆 git log（若有 commit history）。
   - 若為空 repo，標記為「空專案，建議封存或確認用途」。

2. **判斷歸屬**：
   - 對照組別職責表（見 team-building README.md），判斷最適合的組別。
   - 若職責明顯跨多組 → 進入步驟 3 評估拆解。
   - 若無法判斷 → 記入 ASK_HUMAN.md 請示使用者。

3. **評估拆解**：
   - 識別專案中職責明顯不同的區塊（如 infra 設定 vs. app 邏輯）。
   - 每個區塊是否可獨立運作？是否有各自的變更頻率？
   - 若可拆 → 記錄拆解建議：哪些檔案/目錄歸哪組。
   - 若不可拆或成本過高 → 歸主要職責所屬組別，備註次要職責。

4. **評估封存**：
   - 最近 commit 距今超過 12 個月 + 無明確用途 → 建議封存。
   - 封存 ≠ 刪除，僅標記為不活躍，保留於 `_uncategorized/` 或 archive。

5. **記錄結論**：
   - 更新 `_uncategorized/README.md` 中該 repo 的狀態。
   - 若決定歸屬：在 AGENT_PLAN.md 新增「將 X repo 移至 Y 組目錄」待辦。
   - 若決定拆解：在 AGENT_PLAN.md 新增拆解步驟。
   - 若需請示：寫入 ASK_HUMAN.md。
