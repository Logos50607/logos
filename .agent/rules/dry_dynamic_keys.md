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
