---
name: adoption-principles
trigger: always_on
description: "外部技能吸納的核心原則與優先級規範，所有引入行為必須遵守。"
---

# 外部技能吸納原則

## 核心原則

1. **SSOT 不可破壞**：引入的外部技能不得成為第二個 source of truth；自有 discipline 體系始終為最終權威。
2. **選擇性引入**：不整包吃，只挑經評估後有價值的項目建立 adapter。
3. **可追蹤性**：必須保留與上游的版本關聯，以便追蹤更新與變更。
4. **格式一致性**：引入後的技能必須符合組織 discipline metadata 格式，對內部系統透明。

## 優先級規範

- 自有 **rules** 為最高優先級。
- 引入的外部技能與自有 **skills** 同級。
- 當外部技能的指引與自有 rules 衝突時，以 rules 為準。

## 目錄結構慣例

外部來源統一掛載於目標 repo 的 `.agent/skills/_vendor/` 下，與自有 skill 物理隔離：

```
.agent/skills/
├── _vendor/              # 外部來源掛載區
│   └── <source-name>/    # 具體來源（透過版控機制掛載）
├── <skill-name>/         # adapter：引用 _vendor 內容的自有 SKILL.md
└── <existing-skill>/     # 原有 skill，不受影響
```
