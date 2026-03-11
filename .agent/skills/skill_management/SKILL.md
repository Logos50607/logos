---
name: skill_management
description: "用於指導 AI 如何建立、組織及維護 Antigravity Skills 系統。當需要建立新技能或優化現有技能結構時使用。"
---

# Antigravity Skills 管理指南

本技能旨在指導 AI 遵循 Antigravity 官方規範，建立高效、易於理解且結構化的「技能
(Skills)」。

## 1. 什麼是 Skills？

Skills 是可重用的知識包、指令及最佳實踐，旨在為 AI
提供特定任務的專業能力。這允許 AI 在需要時才載入特定上下文，保持全域對話的高效。

## 2. 檔案架構規範

每個技能都應放置在獨立的資料夾中，路徑如下：

- **專案專屬技能**: `.agent/skills/<skill-folder>/`
- **全域技能**: `~/.gemini/antigravity/skills/<skill-folder>/`

### 資料夾內容物：

- `SKILL.md` (**必要**): 技能的入口點，包含中繼資料與核心指令。
- `scripts/` (選用): 該技能使用的輔助腳本。
- `examples/` (選用): 參考實作或範例。
- `resources/` (選用): 模板、數據檔案或資產。

## 3. SKILL.md 格式要求

`SKILL.md` 必須以 **YAML frontmatter** 開頭：

```yaml
---
name: <unique-id>
description: "清楚的第三人稱描述，說明此技能的功能以及 AI 應在何時使用它。"
---
```

- **name**: 技能的唯一識別碼（若省略則預設為資料夾名稱）。
- **description**: **關鍵部分**。AI
  會掃描所有技能的描述來決定是否啟用該技能。描述必須準確且具備觸發關鍵字。

## 4. AI 運作流程

1. **發現 (Discovery)**: AI 在對話開始時掃描所有可用技能的名稱與描述。
2. **啟用 (Activation)**: 當使用者要求或上下文匹配時，AI 讀取完整的 `SKILL.md`。
3. **執行 (Execution)**: AI 根據技能內的指令執行任務。

## 5. 最佳實踐

- **單一職責**: 每個技能應專注於解決一個領域的問題。
- **清晰的觸發條件**: 在 `description` 中明確指出適用場景。
- **正體中文**: 根據全域規範，文件內容應使用台灣正體中文。
- **範例引導**: 在 `examples/` 中提供優質範例，協助 AI 理解預期輸出。
- **腳本規模與組態**: 在 `scripts/` 中的腳本檔案應控制在 **100 行以內**。功能過於複雜時應進行模組化切分。
- **索引化設計**: 主要腳本應擔任 **Index / Content List** 的角色，指引 AI 僅關注必要部分。採用 **Pipe (管道)** 或 **Strategy Pattern (策略模式)** 透過注入方式整合功能，保持高階腳本的抽象性。
