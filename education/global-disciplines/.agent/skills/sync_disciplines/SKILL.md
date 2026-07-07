---
name: sync_disciplines
trigger: manual
description: "將 .agent/ 中的 global disciplines 同步至各 agent 的目標位置（antigravity、claude 等）。"
---

# Skill: sync_disciplines

## 用途

根據 `discipline_config.json` 的設定，將 `.agent/rules`、`.agent/workflows`、`.agent/skills`
同步至對應 agent 的目標路徑。

## 執行方式

```bash
bash /home/logos/.gemini/.agent/skills/sync_disciplines/scripts/sync.sh <agent_name>
```

| agent | 說明 |
|-------|------|
| `antigravity` | 同步至 Gemini CLI 工作目錄 |
| `claude` | 同步至 `~/.claude/`（全域 Claude Code）|

## 分級載入 (Tiered Loading)

`insert_text` 策略依 rule 檔 frontmatter 的 `trigger` 決定注入方式（依據：`discipline_metadata` §3）：

| trigger | 注入方式 |
|---------|----------|
| `always_on`（或未宣告） | 全文注入（維持 START_FILE / MD5 marker 格式） |
| `model_decision` / `glob` / `manual` | 不注入全文，彙整至注入區塊尾端的**條件式規則索引** |

索引格式（Markdown 表格）：

```
## 條件式規則索引（相關任務時先讀全文再行動）

| 規則 | 觸發 | 何時必讀 | 路徑 |
|------|------|----------|------|
| scraping_methodology | model_decision | 爬蟲開發方法論：… | /home/logos/.gemini/.agent/rules/scraping_methodology.md |
```

- 「何時必讀」直接取該規則的 `description`，因此非 always_on 規則的 description 必須寫明觸發時機。
- 無 trigger 欄位的檔案保守視為 always_on。
- glob 規則的觸發欄附上 `globs` 值。

## 測試

```bash
bash /home/logos/.gemini/.agent/skills/sync_disciplines/scripts/test_sync.sh
```
