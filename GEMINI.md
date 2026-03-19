---
name: global_guidelines_index
description: "Antigravity 全域 Discipline 索引，定義了全域適用的規則、工作流與技能。"
---

<!-- DISCIPLINE_START: rules -->
<!-- START_FILE: agent_behavior.md (MD5: b8e470415c3fd18a2587b88517642643) -->
---
trigger: always_on
description: "AI 行為與維護規範，包含重複指令限制與規則、技能的主動維護。"
---

# AI 行為與維護規範 (AI Behavior & Maintenance)

本規則旨在提升 AI 在開發過程中的效率與主動性，並規範異常情況下的處理邏輯。

## 1. 主動維護規則與技能

- **持續學習**：在討論過程中發現全域或特定專案的慣例、重複模式或應正規化的專門任務時，AI
  應主動將其正式化。
- **規則更新**：主動請示使用者在全域或特定工作區下之 `README.md`,
  `.agent/rules`, `.agent/skills` 或 `.agent/workflows`
  目錄中建立或更新相關文件。
- **一致性**：確保所有 metadata 遵循專案標準格式（例如 Markdown、YAML
  frontmatter）。

## 2. 專案初始化規範

- **強制初始化**：當進入一個新專案，若發現其根目錄並無 `.agent/` 目錄，或者
  `.agent/rules/` 中並未載入任何該專案的規範時，AI **必須優先執行**
  `/setup-project` 工作流。

## 3. 溝通風格

- **視情況調整**：使用者的溝通風格會依情境不同而變化，不應預設對方永遠言簡意賅。簡短指令代表方向明確，不代表排斥討論。

## 4. 重複指令限制

- **主動中斷**：當重複類似指令或操作 3
  次以上（如連續失敗的嘗試或無進展的循環操作）時，AI **必須主動中斷**當前流程。
- **切換做法**：AI
  應主動重新分析問題、採用不同工具或向使用者尋求進一步說明（例如在
  `ASK_HUMAN.md` 紀錄）。
<!-- END_FILE: agent_behavior.md -->

<!-- START_FILE: development_guidelines.md (MD5: 121254d94d2fe8a0eec7f030613b118a) -->
---
name: development_guidelines
trigger: always_on
description: "開發與重構品質規範，要求任務執行（開發、重構、優化）必須遵循測試驅動、依賴管理與模組化原則。"
---

# 開發與重構規範 (Development & Refactoring Guidelines)

本規則旨在確保專案開發與重構過程中的一致性與品質，所有開發與重構行為必須遵循以下規範：

## 1. 語言優先權 (Language Priority)

- **優先順序**：除非功能過於複雜，必須引入特定語言套件，否則腳本語言一律以
  **sh** 優先於 **py**，再優先於 **js**。

## 2. 測試驅動 (Script Testing)

- **必須執行測試**：在提交程式碼前，必須確保測試腳本執行通過。
- **測試位置**：測試腳本應放置在原腳本所在目錄下，並以 `test_` 為前綴。
- **端到端驗證**：除腳本測試外，應主動確認機制是否真正生效（例如 sync 後確認目標檔案確實被載入，而非僅確認腳本執行不報錯）。

## 2. 依賴管理 (Dependency Tracking)

- **集中記錄**：所有功能或腳本所需的外部依賴（工具、套件、庫）必須記錄在專案根目錄的
  `DEPENDENCIES.md` 中。
- **格式要求**：列出依賴名稱、版本要求（如有）、用途以及安裝/安裝檢查方式。
- **持續更新**：新增任何依賴時，必須同步更新 `DEPENDENCIES.md`。

## 4. 設計原則 (Design Principles)

- **關注點分離**：不同層級（global vs. project）、不同職責的邏輯必須嚴格分開，不得混入同一個檔案或設定。
- **設計一致性**：同類的問題應採用相同的設計語言（例如同樣採用 Strategy Pattern、同樣的 config-driven 方式），不可一個用策略模式、另一個 hardcode。
- **命名即設計**：命名應清楚反映責任範疇，同層級的元件應有一致的命名風格。

## 3. 腳本規模與結構 (Script Scale & Structure)

- **行數限制**：單一腳本檔案應盡可能控制在 **100
  行以內**。若功能過於複雜導致超過 100 行，應主動進行模組化切分。
- **索引化設計**：每個主要腳本應具備 **Index / Content List**
  的特質，作為導航，讓 AI 僅需閱讀與當前任務相關的部份。
- **解耦與注入**：
  - 核心邏輯採用 **Pipe (管道)** 或 **Strategy Pattern (策略模式)**
    等設計模式實作。
  - 將具體的功能邏輯以「注入」的方式傳遞給高階腳本，避免硬編碼。
  - 確保高階腳本主要負責協調與流程導航，實作細節隱藏在模組化的子腳本或專責模組中。
<!-- END_FILE: development_guidelines.md -->

<!-- START_FILE: discipline_metadata.md (MD5: 957be2987fc7e28bb328fe40e595fe01) -->
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

## 2. 範例

```yaml
---
name: rule_management
description: "用於指導 AI 如何建立、組織及維護 Antigravity Rules。當需要規範 AI 行為、程式碼風格或專案特定約束時使用。"
---
```
<!-- END_FILE: discipline_metadata.md -->

<!-- START_FILE: git_usage.md (MD5: e04a920b6793ca9ed49fa4eb7605a2bf) -->
---
name: git_usage
trigger: always_on
description: "Git 版控規範，定義了自動提交機制與訊息格式要求。"
---

# Git 提交規範 (Git Commit Convention)

本規則旨在確保專案歷史紀錄的整潔、清晰及具備語義。

## 1. 自動提交規範

- **即時提交**：在任何檔案變更（建立、修改、更名、刪除）後，AI **必須立即執行**
  `/git-commit` 工作流。
- **訊息格式**：Commit
  訊息應簡明地說明修改內容，並統一使用**台灣正體中文**。建議使用常見的前綴（例如
  `feat:`, `fix:`, `doc:`, `chore:`, `refactor:`）。
<!-- END_FILE: git_usage.md -->

<!-- START_FILE: language.md (MD5: e6ef9be7d59e4141ea72b520f5dcc6a9) -->
---
name: language
trigger: always_on
description: "強制要求使用台灣正體中文進行溝通與文件撰寫。"
---

# 語言規範 (Language Rules)

應始終使用**台灣正體中文**（Traditional Chinese,
Taiwan）與使用者進行溝通，並在撰寫文件、註解及提交訊息時遵循此規範。
<!-- END_FILE: language.md -->

<!-- START_FILE: project_setup_files.md (MD5: c43e55602c9d2b4de753817838c8581f) -->
---
name: project_setup_files
trigger: always_on
description: "專案結構與管理清單規範，定義了 .agent 目錄以及 AGENT_PLAN/ASK_HUMAN 的用途。"
---

# 專案結構與清單規範 (Project Setup & Lists)

本規則旨在確保專案結構化，並透過清單管理 AI 與使用者的互動。

## 1. 核心結構

- `.agent/rules/`：存放專案規範。
- `.agent/skills/`：存放專案輔助技能。
- `.agent/workflows/`：存放 slash commands 及自動化流程。
- `.agent/INDEX.md`：(可選) 由 `sync_disciplines` 或 `/setup-project`
  自動生成，作為 rules/skills/workflows 的索引。
- `README.md`：參照 global 的 readme rule 建立。

## 2. 管理清單 (TODOLIST)

在專案根目錄必須始終維護下列管理清單 (TODOLIST)：

- **`AGENT_PLAN.md`**：記錄 AI 計畫執行的事項。
- **`ASK_HUMAN.md`**：記錄需請示使用者的項目、衝突或未驗收的任務。
- **格式規範**：遵循 `todolist_format.md`。

## 3. README 優先原則

- **主動讀取**：對話開始、分析功能或進入子目錄時，優先讀取該目錄下的
  `README.md`。
- **維護職責**：確保 `README.md`
  清楚說明目錄結構、程式碼邏輯及使用方式，以便後續開發。
<!-- END_FILE: project_setup_files.md -->

<!-- START_FILE: readme_management.md (MD5: 9abb2ba9090db76c852de3aaed09616a) -->
---
trigger: always_on
description: "README 優先原則，要求 AI 主動讀取並維護各目錄下的 README.md，以確保專案背景資訊同步。"
---

# README 管理規範 (README Management)

本規則旨在確保專案各層級的開發背景、結構與使用方法都能透過 `README.md`
得到妥善記錄。**README 文件必須幫助使用者、開發者與 AI
快速理解該工具或功能想解決什麼問題、如何使用、以及運作原理。**

## 1. README 優先原則 (Read First)

- **主動讀取**：在對話開始、分析新功能或進入任何子目錄時，AI
  **必須優先讀取**該目錄下的 `README.md`。

## 2. 維護與更新職責 (Maintenance)

- **主動評估**：每次執行工作任務時，AI 應評估是否需要更新受影響目錄的
  `README.md`。
- **維護職責**：確保記錄內容與實際程式碼邏輯同步，以便後續開發者或 AI 理解。

## 3. 內容品質要求 (Content Requirements)

每個 `README.md` 應至少包含以下要素：

- **核心目標 (Core Goal)**：清晰描述該目錄及其轄下檔案旨在「解決什麼問題」。
- **結構索引 (Structure
  Index)**：列出該目錄的主要檔案與子資料夾，提供簡要功能概述。
- **使用指南 (Usage
  Guide)**：說明「如何使用」該功能或工具，包含前置作業、執行指令、參數說明或注意事項。
- **實作原理 (Implementation
  Details)**：簡述「運作原理」與核心邏輯，幫助開發者與 AI 理解其內部流程。
<!-- END_FILE: readme_management.md -->

<!-- START_FILE: todolist_format.md (MD5: 84b2c7ac47c3087e443ece677518df55) -->
---
name: todolist_format
trigger: glob
globs: "AGENT_PLAN.md ASK_HUMAN.md TODOLIST.md ASKHUMAN.md"
description: "規範 AGENT_PLAN (TODOLIST) 與 ASK_HUMAN (ASKHUMAN) 的格式要求，包含日期標記與排序規則。"
---

# 清單格式規範 (List Format Guidelines)

當編輯 `AGENT_PLAN.md` (或 `TODOLIST.md`) 與 `ASK_HUMAN.md` (或 `ASKHUMAN.md`)
時，必須遵循以下格式：

- **格式規範**：
  - 使用條列表 (`- [ ]`, `- [x]`)。
  - 標號後加上日期 (格式：`YYYY-MM-DD`)。
  - **最新日期優先**：新加入的項目應置於文件最上方。
<!-- END_FILE: todolist_format.md -->

<!-- START_FILE: web_content_extraction.md (MD5: 23c820e9e4ac5c462e33c3b9d52ec438) -->
---
name: web_content_extraction
trigger: manual
description: "定義何時應使用 /fetch_web_content 工作流來獲取網頁內容。"
---

# 網頁內容擷取規範 (Web Content Extraction Guidelines)

當需要獲取外部資訊時，應遵循以下使用時機與規範：

## 1. 使用時機

- **調研與參考**：當使用者提供 URL 並要求分析、總結或參考該網頁內容時。
- **自動化補全**：當需要特定文檔或網頁數據來輔助程式碼撰寫，且已知該數據存在於特定
  URL 時。
- **禁止行為**：嚴禁在未經使用者許可的情況下，頻繁或大規模爬取無關網頁。

## 2. 執行流程

- 始終優先執行 `/fetch_web_content` 工作流。
- 確保擷取的內容經過 Markdown 轉換，以節省 Token 並提高 AI 閱讀效率。
<!-- END_FILE: web_content_extraction.md -->

<!-- DISCIPLINE_END: rules -->

---

## Discipline 同步機制

所有 disciplines（rules、workflows、skills）的**唯一來源**為 `/home/logos/.gemini/.agent/`，透過 `sync_disciplines` skill 同步至各 agent 的目標位置。

### 支援的 Agent

| Agent | 目的 | 同步指令 |
|-------|------|---------|
| `antigravity` | 同步至 Gemini CLI 的工作目錄 | `bash .agent/skills/sync_disciplines/scripts/sync.sh antigravity` |
| `claude` | 同步全域 disciplines 至 `~/.claude/` | `bash .agent/skills/sync_disciplines/scripts/sync.sh claude` |

### Claude 整合說明

`claude` agent 將 disciplines 整合進 Claude Code 的**全域**目錄結構（`~/.claude/`）：

```
~/.claude/
├── CLAUDE.md       ← rules 注入（insert_text 策略）
└── commands/       ← workflows 軟連結（soft_link 策略）
    ├── git-commit.md
    ├── setup-project.md
    └── fetch-web-content.md
```

**執行全域同步**
```bash
cd /home/logos/.gemini
bash .agent/skills/sync_disciplines/scripts/sync.sh claude
```

執行後，所有 Claude Code session 都會自動載入：
- 所有全域 rules（透過 `~/.claude/CLAUDE.md`）
- 所有 slash 指令 `/git-commit`、`/setup-project`、`/fetch-web-content`（透過 `~/.claude/commands/`）

> 專案層級的 discipline 同步由各專案自行維護，此處僅處理全域（user-level）設定。
