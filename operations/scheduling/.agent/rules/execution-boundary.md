---
name: execution-boundary
trigger: always_on
description: "定義排程任務中腳本層與評估層的分界，確保機械操作與 AI 判斷不混淆。"
---

# 腳本層與評估層分界

## 分層定義

### 腳本層（`command.type = script`）

- 執行 shell 腳本，進行資料蒐集、檔案操作、API 呼叫等機械操作。
- 結果為確定性的，不包含主觀判斷。
- 以 exit code 判斷成敗：`0` = success，非 `0` = failure。
- stdout / stderr 直接作為執行報告的「輸出」區段。

### 評估層（`command.type = ai-evaluate`）

- 可選的前置步驟：先執行 `script_path`（若有）蒐集結構化資料。
- 讀取 `prompt_path` 的 prompt 檔案內容。
- 將蒐集的資料與 manifest body 的補充說明注入 prompt。
- 透過 `claude -p` 執行 AI 評估。
- AI 的判斷結果寫入報告的「輸出」區段。
- 由 AI 輸出中的明確結論判斷 status（需在 prompt 中定義成功/失敗條件）。

## 禁止行為

- **不得在腳本層中嵌入 AI 呼叫**：腳本層的職責是蒐集資料與機械操作，判斷邏輯屬於評估層。
- **不得在評估層中執行不可逆操作**：AI 評估的輸出應為判斷結論與建議行動，不得直接刪除檔案、修改資料庫或發送通知。若需執行不可逆操作，應由後續的人工審核或獨立腳本處理。
- **不得讓評估層覆蓋腳本層已產出的結構化資料**：腳本產出的原始資料必須完整保留於報告中，AI 評估結論為附加而非替換。

## 判斷指引

| 情境 | 應使用的類型 |
|------|-------------|
| 檢查檔案是否存在、服務是否在線 | `script` |
| 蒐集 log 並判斷是否有異常趨勢 | `ai-evaluate`（script 蒐集 log，AI 判斷趨勢）|
| 執行資料備份 | `script` |
| 評估外部工具是否需要版本更新 | `ai-evaluate` |
| 定期清理過期暫存檔 | `script` |
| 審閱本週程式碼變更是否符合規範 | `ai-evaluate` |
