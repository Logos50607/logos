---
name: discipline_metadata
trigger: glob
description: "用於確保 GEMINI.md 與所有 Discipline (規則、技能、工作流) 檔案包含必要的元資料 (Metadata)。"
globs: "GEMINI.md .agent/rules/**/*.md .agent/skills/**/*.md .agent/workflows/**/*.md"
---

# Discipline Metadata 規範

為了確保 AI 能正確識別並理解各個 Discipline 的目的，所有 `GEMINI.md` 以及位於
`.agent/rules`, `.agent/skills`, `.agent/workflows`
目錄下的檔案，必須在檔案最開頭包含 YAML Frontmatter 格式的 Metadata。

## 1. 格式要求

必須包含以下欄位：

- `name`: 該檔案或規範的簡短唯一名稱。
- `description`: 對該檔案內容、用途及適用場景的簡要描述。

選填欄位：

- `trigger`: 如果是 `./agent/rules/**/*.md`，必須加入 trigger；內容為
  "always_on", "model_decision", "glob", 或 "manual"。
- `glob`： 如果 trigger 的值是 "glob"，則必須決定所適用的檔案路徑之模式。

## 2. Global Discipline 額外規範

- **SSOT**：Global disciplines 的唯一來源為 `~/.gemini/.agent/`，修改必須在此進行，再透過 sync 同步至各 agent。
- **不得與任何特定專案耦合**：global disciplines 不得包含專案特定的欄位名稱、路徑、程式碼片段或業務邏輯。
- **使用者層級事實不在此限**：本體系服務單一使用者，使用者本人的事實（身分、環境、工具、偏好）**可以**寫入 global disciplines，但仍須按關注點分離歸入對應規則（如身分入 git_usage、環境入 workstation-environment），不得聚合成單一 profile 大雜燴檔。
- 範例若有必要，應使用抽象的佔位名稱（如 `keyA`、`featureX`），而非實際業務欄位。

## 3. Trigger 載入策略 (Loading Policy)

- **`always_on`**：全文注入每個 session 的 context（sync 時寫入 GEMINI.md / CLAUDE.md）。保留給**跨任務皆適用的行為基線**；新增 always_on 規則前必須先問：「每個 session 都需要這條嗎？」
- **`model_decision` / `glob` / `manual`**：不注入全文，只出現在注入的**條件式規則索引**中（name、觸發條件、description、檔案路徑）。agent 判斷當前任務相關時，自行讀取全文再行動。
- 因此非 always_on 規則的 `description` 必須寫明**何時必讀**（例如「起任何服務前」「撰寫爬蟲時」）。
- **機制優先於條文**：規則的效力來自機制（注入、hook、測試、CI），不是條文數量。能用 hook 或腳本強制的行為，優先做成機制，條文只記載原則與理由。

## 4. 範例

```yaml
---
name: rule_management
description: "用於指導 AI 如何建立、組織及維護 Antigravity Rules。當需要規範 AI 行為、程式碼風格或專案特定約束時使用。"
---
```
