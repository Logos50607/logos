---
name: skill-vs-tool
trigger: always_on
description: "區分 skill 與 tool 的判斷準則：何時留在 .agent/skills/，何時應獨立發布為工具。"
---

# Skill 與 Tool 的區別

## 核心問題

> 這個能力，logos 以外的情境會用到嗎？

| | Skill | Tool |
|--|-------|------|
| **本質** | 指導 AI agent 行為的 markdown 文件 | 可獨立執行的程式碼或腳本 |
| **使用者** | logos monorepo 內的 AI agents | 任何專案、任何人 |
| **存放位置** | `.agent/skills/` | 獨立 repo 或套件，delivery 組負責發布 |
| **依賴** | 依賴 logos 的組織結構與 disciplines | 不得依賴 logos monorepo 內部路徑 |

## 判斷流程

```
這個東西是可執行的程式碼/腳本？
  ↓ 否 → 是 AI 行為指引 → Skill，放 .agent/skills/
  ↓ 是
logos 以外也會需要這個能力？
  ↓ 否 → 放組內，不需獨立
  ↓ 是
→ Tool，交 delivery 組規劃獨立發布
   logos 內改為援引（.agent/skills/ 寫使用方式）
```

## 典型案例

| 案例 | 分類 | 原因 |
|------|------|------|
| `call-team`（跨組 -p 封裝） | Skill | 只服務 logos 內各組 |
| `escalate-to-supervision` | Skill | logos 組織結構專屬 |
| `sync_disciplines` | Skill + 腳本 | 僅服務 logos disciplines 體系 |
| `switchboard`（LINE 通訊） | **Tool** | LINE 訊息能力與 logos 組織無關，外部專案也可能需要 |
| `gemini-web`（Playwright UI 自動化） | **Tool 候選** | Gemini Web 操作能力與 logos 無關，但尚未有外部需求確認 |

## 升格為 Tool 的條件

滿足以下任一條件，才啟動獨立發布流程：
1. 已有 logos 以外的實際使用需求
2. 功能本身與 logos 組織架構完全無耦合，且具備明確的 API 介面

**不因「未來可能有人用」而提前獨立。**
