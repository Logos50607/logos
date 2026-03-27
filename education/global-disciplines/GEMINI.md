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

<!-- START_FILE: development_guidelines.md (MD5: 6884ea3a8688120930d43666cd8bc649) -->
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

## 4. 命名規範 (Naming Convention)

- **語言**：目錄名與檔案名一律使用英文，採 kebab-case 格式。中文僅用於文件內容、註解與 commit message。
- **一致性**：同層級的目錄與檔案應有統一的命名風格，避免混用 camelCase、snake_case 與 kebab-case。

## 5. 設計原則 (Design Principles)

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

<!-- START_FILE: discipline_metadata.md (MD5: 537d3a192b27d9f0c7a714047c3f1cf2) -->
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
- 範例若有必要，應使用抽象的佔位名稱（如 `keyA`、`featureX`），而非實際業務欄位。

## 3. 範例

```yaml
---
name: rule_management
description: "用於指導 AI 如何建立、組織及維護 Antigravity Rules。當需要規範 AI 行為、程式碼風格或專案特定約束時使用。"
---
```
<!-- END_FILE: discipline_metadata.md -->

<!-- START_FILE: doc_before_impl.md (MD5: d4d88110e2b7b853449bd53a34fbc94d) -->
---
name: doc_before_impl
trigger: always_on
description: "強制要求先寫文件再實作，確保所有 AI agent 對設計有共同記憶，避免各自解讀。"
---

# 文件優先規範 (Documentation Before Implementation)

## 核心規則

**任何實作（程式碼、腳本、設定）動工前，必須先建立或更新對應的設計文件。**

文件是 AI agents 的共同記憶。沒有文件，下一個 agent 只能從程式碼逆向推測意圖，導致設計漂移。

## 適用範圍

- 新功能、新專案：先寫 `README.md`（核心目標、架構、介面），再開始實作
- 新模組 / channel / adapter：先在 README 或對應文件描述其定位與介面，再建立檔案
- 跨組別介面：先在雙方的 README 明確記載 input/output 格式，再實作串接

## 文件與實作的順序

```
設計討論 → 更新 README / 規範文件 → commit → 實作 → commit
```

不允許：先實作、完成後補文件。

## Why

AI agents 沒有持久記憶，每次對話從文件重建上下文。若文件落後於實作，後續 agent 讀到的是過時設計，會做出與當前程式碼不一致的決策。文件是唯一的共同記憶。
<!-- END_FILE: doc_before_impl.md -->

<!-- START_FILE: dry_dynamic_keys.md (MD5: 4a3f6dc038fb901454a59cb12410fbaa) -->
---
name: dry_dynamic_keys
trigger: always_on
description: "禁止對多維度相同操作硬編碼每個 key，應以動態迭代統一處理，確保 DRY 與單一來源原則。"
---

# DRY：動態 Key 迭代規範 (Dynamic Key Iteration)

## 核心規則

對多個維度（欄位）執行**相同操作**（score、distance、transform、validate 等）時，
**禁止**逐一硬編碼每個 key，必須以動態迭代統一處理。

## 原則

- **Single Source of Truth**：維度清單只在一處定義（通常是 type、schema 或 config 物件的 key），函式本身不感知具體欄位名稱。
- 新增或移除維度時，只改 type/config，不改運算邏輯。
- 適用語言：`Object.keys` + `reduce`（JS/TS）、dict iteration（Python）、reflection（Go/Java）等，語言不限，原則相同。
- 適用場景：score、distance、penalty、transform、validate、normalize 等對多欄位做相同運算的模式皆適用。
<!-- END_FILE: dry_dynamic_keys.md -->

<!-- START_FILE: git_usage.md (MD5: 6fdfd31926d18b571223e5efc8823e5c) -->
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

## 2. Amend 規範

- **略為修正直接 amend**：若變更屬於對上一次 commit 的微幅修正（如 typo、路徑修正、格式調整），應使用 `git commit --amend` 併入上一個 commit，而非產生新的 commit。
- **獨立變更則新增 commit**：若變更涉及新功能、不同檔案群組或與上一次 commit 無直接關聯，則應建立新的 commit。
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

<!-- START_FILE: modular_decomposition.md (MD5: 4105a36b14b3a3056027ed194b7c0bd9) -->
---
name: modular_decomposition
trigger: always_on
description: "專案模組拆解原則：何時抽離、抽到哪、personal 如何援引、如何交付。"
---

# 模組拆解原則 (Modular Decomposition)

## 核心判斷：這段邏輯屬於誰？

對每個模組問三個問題：

1. **是否只服務這個專案？** → 留在 personal
2. **是否有其他專案可能需要相同能力？** → 抽到對應組別
3. **是否是這個專案對通用能力的特定配置？** → 留在 personal，但以 skill 援引組別模組

## 抽離方向：按職責對應組別

| 職責 | 目標組別 |
|------|----------|
| 爬蟲、外部資料取得 | `intelligence/` |
| AI 生成、媒體製作 | `creation/` |
| 摘要、教材、報告設計 | `education/` |
| 定期執行、排程 | `operations/` |
| 環境、硬體、基礎建設 | `infrastructure/` |

## Personal 專案的角色：薄消費者

抽離後，personal 專案應該是**薄的消費者**，不複製邏輯：

- 保留：專案特定的配置、資料、輸入輸出
- 移除：可被複用的功能邏輯
- 取代方式：在 `.agent/skills/` 寫一份 **援引技能（reference skill）**，說明如何呼叫組別模組

### 援引技能範本

```markdown
---
name: use-<module>
description: "如何從本專案呼叫 <group>/<module>"
---

# 呼叫 <module>

模組位置：`/data/logos/<group>/<module>/`

## 使用方式
<執行指令、參數說明、輸入輸出格式>

## 本專案的配置
<說明本專案傳入的特定參數或資料路徑>
```

## 拆解時不要過度抽象

- **不要**因為「未來可能用到」就抽離
- **要**當同一邏輯出現在 2 個以上的專案時才抽離
- 拆解前先文件化設計，再動程式碼

## 交付設計（Delivery）

當模組被抽離至 monorepo 後，若需要打包給外部使用：

1. **路徑引用**（內部使用）：personal 專案直接引用 `/data/logos/<group>/<module>/`，適合工作站環境
2. **Build 複製**（交付外部）：delivery 組負責建立 `build.sh`，將依賴的組別模組複製至獨立 package
3. **套件化**（長期）：成熟模組可發布為獨立 pip/npm 套件，personal 改為 `pip install` 引用

選擇原則：
- 僅自用 → 路徑引用
- 給熟悉 monorepo 的人 → 路徑引用 + 說明
- 給外部 / 獨立部署 → Build 複製或套件化

## 排程與核心行為分離

任何模組若有「可排程執行」的能力，**必須**把核心行為與排程觸發分開：

- **核心**：純函式或腳本，可直接呼叫，不依賴排程框架
- **排程 adapter**：薄包裝，呼叫核心並符合 `operations/scheduling` 的 manifest 格式

這樣在排程之外（測試、手動觸發、其他 agent 呼叫）也能直接使用核心行為。
<!-- END_FILE: modular_decomposition.md -->

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
