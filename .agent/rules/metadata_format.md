---
name: metadata_format
trigger: glob
description: "用於確保 GEMINI.md、規則、技能與工作流檔案包含必要的元資料 (Metadata)。"
globs: "GEMINI.md .agent/rules/**/*.md .agent/skills/**/*.md .agent/workflows/**/*.md"
---

# Metadata 規範 (Metadata Rules)

為了確保 AI 能正確識別並理解各個規範檔案的目的，所有 `GEMINI.md` 以及位於
`.agent/rules`, `.agent/skills`, `.agent/workflows`
目錄下的檔案，必須在檔案最開頭包含 YAML Frontmatter 格式的 Metadata。

## 1. 格式要求

必須包含以下欄位：

- `name`: 該檔案或規則的簡短唯一名稱。
- `description`: 對該檔案內容、用途及適用場景的簡要描述。

選填欄位：

- `trigger`: 如果是 ./agent/rules/**/*.md ，必須加入 trigger；內容為
  "always_on", "model_decision", "glob", 或 "manual"。
- `glob`： 如果 trigger 的值是 "glob"，則必須決定所適用的檔案路徑之模式；例如
  "GEMINI.md .agent/rules/**/*.md .agent/skills/**/_.md
  .agent/workflows/**/_.md" 。

## 2. 範例

```yaml
---
name: rule_management
description: "用於指導 AI 如何建立、組織及維護 Antigravity Rules。當需要規範 AI 行為、程式碼風格或專案特定約束時使用。"
---
```
