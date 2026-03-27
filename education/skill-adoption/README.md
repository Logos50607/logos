# Skill Adoption — 外部技能吸納專案

## 核心目標 (Core Goal)

提供教育組一套可執行的 workflow，用於系統性地評估、引入與維護來自外部的技能（skill），確保引入行為符合組織 discipline 體系且不違反 SSOT 原則。

## 背景

隨著 AI agent 生態成熟，社群與開源專案持續產出高品質的 skill/workflow 定義。本專案定義了「怎麼吸納」的標準流程，而非針對特定來源的一次性處理。

## 結構索引 (Structure Index)

```
skill-adoption/
├── .agent/
│   ├── rules/
│   │   └── adoption-principles.md   # 核心原則與優先級規範
│   └── workflows/
│       ├── evaluate-source.md        # 評估外部來源（初篩 + 深度評估）
│       ├── adopt-skills.md           # 掛載 vendor + 撰寫 adapter
│       └── maintain-vendor.md        # 定期維護：更新 / 退場 / 內化
├── templates/
│   └── ADOPTION_RECORD.md            # 單次引入的紀錄模板
├── records/                           # 各次引入的執行紀錄
│   └── superpowers.md                 # obra/superpowers 引入評估（首案）
├── README.md
├── AGENT_PLAN.md
└── ASK_HUMAN.md
```

## 使用指南 (Usage Guide)

### 評估新的外部來源

```
/evaluate-source
```
提供來源名稱與 URL，workflow 會執行初篩、逐項評估、產出引入紀錄至 `records/`。

### 執行引入

```
/adopt-skills
```
依據已核可的引入紀錄，在目標 repo 中建立 `_vendor/` submodule 與 adapter。

### 定期維護

```
/maintain-vendor
```
檢查已掛載來源的上游狀態，決定更新、退場或內化。建議每季執行一次。

## 實作原理 (Implementation Details)

三個 workflow 對應技能吸納的完整生命週期：

1. **evaluate-source**：發現 → 初篩 → 深度評估 → 產出紀錄
2. **adopt-skills**：掛載 → adapter 撰寫 → sync 驗證 → 提交
3. **maintain-vendor**：盤點 → 檢查上游 → 判斷處置 → 執行

核心原則與目錄結構慣例定義在 `.agent/rules/adoption-principles.md`，所有 workflow 執行時自動遵守。
