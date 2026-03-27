# 外部 Skill 引入策略

## 核心目標 (Core Goal)

定義從外部來源（如 obra/superpowers）引入 skill 的標準機制，確保不違反 SSOT 原則、不產生重工、且可追蹤上游更新。

## 問題

直接複製外部 skill 進 `.agent/skills/` 會導致：
- 無法追蹤上游更新
- 與自有 discipline 格式不一致
- 違反 SSOT 原則

## 方案：git submodule + adapter 層

```
.agent/skills/
├── _vendor/                    # git submodule 掛載外部來源
│   └── superpowers/            # submodule → obra/superpowers
├── brainstorming/              # adapter：自己的 SKILL.md 引用 _vendor
├── test-driven-development/    # adapter：自己的 SKILL.md 引用 _vendor
└── sync_disciplines/           # 原有 skill，不受影響
```

### 設計要點

1. **_vendor/** — 用 `git submodule` 掛載外部 repo，保留上游版本追蹤
2. **adapter SKILL.md** — 每個要引入的 skill 建一個 adapter，符合 discipline metadata 格式（name, description, trigger），內容引用 `_vendor/` 下的原始 skill 並加上本地化調整
3. **選擇性引入** — 不是整包吃，只挑需要的 skill 建 adapter
4. **sync 相容** — 現有的 `sync_disciplines` 機制不需改動，adapter 本身就是標準 SKILL.md

## 優先級衝突處理

Superpowers 定義了優先級：user instructions > superpowers > system prompt。與現有 discipline 系統的對齊方式：

- 自有 **rules = 最高**（等同 superpowers 的 user instructions）
- 引入的 superpowers skills = **與自有 skills 同級**，衝突時以 rules 為準

## Superpowers 引入評估

### 建議引入（與現有 discipline 互補）

| Superpowers Skill | 價值 | 與現有重疊 |
|---|---|---|
| brainstorming | 高 — 強制需求釐清 | 無重疊 |
| writing-plans | 中 — 任務拆解 | 部分重疊 AGENT_PLAN |
| test-driven-development | 高 — 嚴格 TDD | 補強 development_guidelines |
| systematic-debugging | 高 — 4 階段除錯 | 無重疊 |
| subagent-driven-development | 高 — 平行子 agent | 無重疊，符合團隊架構 |
| using-git-worktrees | 中 — 隔離開發 | 無重疊 |
| requesting/receiving-code-review | 中 — 品質關卡 | 可歸監督組 |

### 不需引入（已有覆蓋）

- writing-skills → 已有 skill_management
- using-superpowers (bootstrap) → 已有 agent_behavior + discipline_metadata

### 建議首批引入

1. **brainstorming** — 最獨立、最高價值
2. **systematic-debugging** — 補強現有缺口
3. **test-driven-development** — 強化測試規範

## 執行歸屬

| 項目 | 負責組 |
|---|---|
| 本策略核可 | 策略組 |
| submodule 機制建置 + adapter 格式制定 | 教育組 |
| sync_disciplines 相容性確認 | 教育組（logos repo 擁有者）|
| 各 skill adapter 撰寫 | 教育組 |
