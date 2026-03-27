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
