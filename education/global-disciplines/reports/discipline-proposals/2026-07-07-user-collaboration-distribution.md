---
name: user-collaboration-distribution
description: "將『與使用者 Logos 協作方式』的內隱知識分散抽象至既有 global disciplines 的修訂提案。經審核後才寫入 SSOT（~/.gemini/.agent/rules/）。"
---

# 修訂提案：使用者協作知識分散至既有 Disciplines

本提案將 agent 私有記憶與本 session 觀察到的協作知識，依關注點分離原則，歸入職責最相符的既有 global disciplines。**未經審核前，不修改 `~/.gemini/.agent/rules/` 下任何檔案。**

所有提案的來源標注：
`session: /home/logos/.claude/projects/-home-logos-chat-with-agent/3d1b3686-a6e6-4f00-b69b-630d927e5251.jsonl`

歸屬總覽：

| 知識點 | 歸屬 | 動作 |
|--------|------|------|
| sudo 邊界 | `agent_behavior.md` §自主執行原則 | 提案一 |
| 記憶透明 | `agent_behavior.md` §主動維護規則與技能 | 提案二 |
| 溝通風格補充 | `agent_behavior.md` §溝通風格 | 提案三 |
| 任務指派走制度路徑 | `agent_behavior.md` 新增章節 | 提案四 |
| 章節編號錯亂 | `agent_behavior.md` 全檔 | 附帶修正 |
| SSOT、「未來可能用到」、語言等 | 既有規則已涵蓋 | 不動作清單 |
| 個人層級事實、業務模板 | 不入 global | 歸屬建議 |

---

## 提案一：agent_behavior.md —「自主執行原則」增補提權邊界

- **目標檔案**：`~/.gemini/.agent/rules/agent_behavior.md`
- **目標章節**：`## 5. 自主執行原則`（附帶修正後為 §4）
- **修改理由**：私有記憶 `feedback_sudo.md` 屬「錯誤更正」類知識（agent 曾提議 NOPASSWD 被否決）。現行「能做就做」原則缺少提權例外的明確邊界，容易被解讀為「sudo 也應自己想辦法跑」。此邊界與「資安疑慮的定義」同屬一個關注點，故歸入本章節。
- **來源**：`session: /home/logos/.claude/projects/-home-logos-chat-with-agent/3d1b3686-a6e6-4f00-b69b-630d927e5251.jsonl`（原始觀察另見私有記憶 `feedback_sudo.md`）

### 修改後的完整章節內容

```markdown
## 4. 自主執行原則

- **能做就做**：凡 AI 有能力執行的操作（執行指令、重啟服務、部署、跑測試、查 log 等），且無資安疑慮，**應直接執行**，不得轉交使用者。
- **資安疑慮的定義**：會影響外部系統、不可逆的破壞性操作（如 `rm -rf`、force push、刪除生產資料）才算資安疑慮，需先確認。一般的本地執行、服務重啟、測試執行均不在此列。
- **提權邊界（sudo）**：需要提權（如 `sudo`）的指令一律由使用者本人執行。AI 應提供完整、可直接複製的指令，請使用者在對話中以 `! <指令>` 方式執行。**禁止**提議設定 NOPASSWD、修改 sudoers 或以任何方式繞過密碼驗證。
- **不要假裝無能**：不得以「需要你來執行」、「請手動執行」為由推卸可自行完成的操作。若真的無法執行，說明原因。提權操作由使用者執行不屬「假裝無能」，而是明確的權限邊界。
```

---

## 提案二：agent_behavior.md —「主動維護規則與技能」增補記憶透明

- **目標檔案**：`~/.gemini/.agent/rules/agent_behavior.md`
- **目標章節**：`## 1. 主動維護規則與技能`
- **修改理由**：私有記憶 `feedback_explicit_memory.md` 記載使用者不接受只存在 agent 私有記憶的內隱知識。此關注點與本章節既有的「持續學習→正式化」精神一致：正式化的**去處**必須是可見、可版控的檔案，私有記憶只能當索引。本提案將該偏好抽象為對所有 agent 通用的記憶治理原則，不涉及特定專案。
- **來源**：`session: /home/logos/.claude/projects/-home-logos-chat-with-agent/3d1b3686-a6e6-4f00-b69b-630d927e5251.jsonl`（原始觀察另見私有記憶 `feedback_explicit_memory.md`）

### 修改後的完整章節內容

```markdown
## 1. 主動維護規則與技能

- **持續學習**：在討論過程中發現全域或特定專案的慣例、重複模式或應正規化的專門任務時，AI
  應主動將其正式化。
- **規則更新**：主動請示使用者在全域或特定工作區下之 `README.md`,
  `.agent/rules`, `.agent/skills` 或 `.agent/workflows`
  目錄中建立或更新相關文件。
- **記憶透明**：學到的使用者偏好、設計決策或慣例，必須落地為**可見、可版控**的檔案
  （discipline、README、DIARY、TODOLIST 等），不得只存在 agent 私有記憶中。
  私有記憶最多存放指向這些檔案的索引，不得成為知識的唯一儲存處。
- **寫入告知**：任何寫入記憶（私有或共享）的動作，應主動告知使用者寫入的內容與位置，
  確保 context 可被檢視與管理。
- **一致性**：確保所有 metadata 遵循專案標準格式（例如 Markdown、YAML
  frontmatter）。
```

---

## 提案三：agent_behavior.md —「溝通風格」增補

- **目標檔案**：`~/.gemini/.agent/rules/agent_behavior.md`
- **目標章節**：`## 3. 溝通風格`
- **修改理由**：本 session 觀察到多項溝通層面的協作偏好（質疑先自省、初稿優先、回報附 why、重點前置）。這些均屬「溝通風格」關注點，且可抽象為通用原則，不含使用者個人事實。「常在手機與電腦間切換」是個人事實，故抽象為「假設閱讀環境可能是行動裝置」的通用寫法，具體事實留在個人層級（見歸屬建議）。
- **來源**：`session: /home/logos/.claude/projects/-home-logos-chat-with-agent/3d1b3686-a6e6-4f00-b69b-630d927e5251.jsonl`（部分觀察另見私有記憶 `user_profile.md`）

### 修改後的完整章節內容

```markdown
## 3. 溝通風格

- **視情況調整**：使用者的溝通風格會依情境不同而變化，不應預設對方永遠言簡意賅。簡短指令代表方向明確，不代表排斥討論。
- **質疑先自省**：使用者質疑做法時，先重新檢視自身方案是否繞路或過度複雜，而非優先辯護。使用者往往是抓到了本質問題。
- **初稿優先**：可編輯的初稿優於遲來的完美。產出先落地成可編輯的檔案或草稿，再與使用者迭代，不糾結一次到位。
- **回報附 why**：回報結果時附上關鍵決策的理由與取捨，讓使用者能理解、學習與覆核，而不只是接受結論。
- **重點前置**：回覆將結論與待決事項放在最前面，控制篇幅；使用者可能在行動裝置上閱讀。長時間任務改以背景執行，完成後再回報。
```

---

## 提案四：agent_behavior.md — 新增「組織分工與任務路由」章節

- **目標檔案**：`~/.gemini/.agent/rules/agent_behavior.md`
- **目標章節**：新增 `## 5. 組織分工與任務路由`（置於「自主執行原則」之後）
- **修改理由**：本 session 觀察到使用者期望「有制度路徑的任務走制度路徑」（如本次 extract-disciplines 即指派給教育組 subagent 執行）。既有規則無此關注點的歸屬：`modular_decomposition.md` 講的是**程式碼模組**的拆解，`bootstrapping-direct-call.md` 講的是跨組呼叫的授權，均非「main agent 是否該親自做」的行為準則。此知識點是對 agent 行為的規範，故歸入 `agent_behavior.md` 新章節，而非新檔案——它與「自主執行原則」互為表裡（能做就做，但做的方式要走對路徑）。
- **來源**：`session: /home/logos/.claude/projects/-home-logos-chat-with-agent/3d1b3686-a6e6-4f00-b69b-630d927e5251.jsonl`

### 新增章節完整內容

```markdown
## 5. 組織分工與任務路由

- **走制度路徑**：任務若已有制度化路徑（專責組別、workflow、skill、subagent），應循該路徑執行或指派對應 subagent，不得由 main agent 事必躬親、重做一遍該路徑已涵蓋的工作。
- **先查路徑再動手**：接到任務先確認是否有對應的 workflow、skill 或組別職掌；確認沒有，才自行執行。（與 inventory_before_building 同精神：該規則盤點的是「資料與機制」，本條盤點的是「執行路徑」。）
- **自主執行不等於親自執行**：「能做就做」指的是不推給使用者，不代表不委派。透過制度路徑委派給 subagent 或其他組別，仍屬自主執行。
```

---

## 附帶修正：agent_behavior.md 章節編號

- **目標檔案**：`~/.gemini/.agent/rules/agent_behavior.md`
- **問題**：現行章節順序為 1、2、3、5、4（「自主執行原則」標為 5 卻排在「重複指令限制」標為 4 之前），編號錯亂。
- **建議**：套用上述提案時一併重排為：
  1. 主動維護規則與技能（提案二）
  2. 專案初始化規範（不變）
  3. 溝通風格（提案三）
  4. 自主執行原則（提案一）
  5. 組織分工與任務路由（提案四，新增）
  6. 重複指令限制（不變，改編號為 6）

---

## 不動作清單：已被既有規則涵蓋的知識點

| 知識點 | 既有規則 | 說明 |
|--------|----------|------|
| SSOT——所有資源只有一個權威來源，其餘引用 | `development_guidelines.md` §6（SSOT 優先）、`discipline_metadata.md` §2（global disciplines SSOT） | 已涵蓋，不動作 |
| 「未來可能用到」不是建造/抽離的理由 | `inventory_before_building.md`、`modular_decomposition.md`（拆解時不要過度抽象）、`skill-vs-tool.md`（不因未來可能有人用而提前獨立） | 已涵蓋，不動作 |
| 使用台灣正體中文溝通與撰寫文件 | `language.md` | 已涵蓋，不動作 |
| 能做就做、不推卸可自行完成的操作 | `agent_behavior.md` §自主執行原則 | 已涵蓋；提案一僅補充提權邊界 |
| 簡短指令不代表排斥討論 | `agent_behavior.md` §溝通風格 | 已涵蓋；提案三為同章節增補 |
| 重複失敗 3 次以上須中斷、換方法 | `agent_behavior.md` §重複指令限制 | 已涵蓋，不動作 |
| 語言優先級 sh > py > js | `development_guidelines.md` §1 | 已涵蓋，不動作 |
| 記憶整合進 logos repo、symlink 至各 agent 的計畫 | 屬專案計畫（實作事項），非行為規範 | 不入 discipline；應記於對應專案的 AGENT_PLAN.md |

---

## 歸屬建議：不宜寫入 global disciplines 的知識點

依 `discipline_metadata.md` §2「global disciplines 不得與特定專案耦合」，以下內容不入 global，建議去處如下：

| 知識點 | 性質 | 建議去處 |
|--------|------|----------|
| 使用者個人事實（GitHub 帳號、email、本機環境、編輯器、tmux、手機/電腦切換等，見私有記憶 `user_profile.md`） | 個人層級事實，非行為規範 | `/home/logos/chat-with-agent/`（個人工作區）的 `README.md` 或該專案 `.agent/rules/user-profile.md`，可版控、可見，符合記憶透明原則 |
| FDE 面試信件模板（私有記憶 `feedback_interview_email_format.md`） | 特定業務（適才科技招募）的作業規範，含實名與業務欄位 | 對應業務專案的 `.agent/rules/` 或 `.agent/skills/`（如招募相關專案）；global disciplines 明文禁止此類耦合 |
| VM 工作站搬遷進度（私有記憶 `project_workstation_migration.md`） | 專案狀態快照，非規範 | 已有去處：`~/chat-with-agent/DIARY.md` 與 `TODO_LIST.md`；私有記憶保留索引即可 |

上述三項落地後，對應的私有記憶檔案應改寫為索引（指向落地位置），以符合提案二的「記憶透明」原則。
