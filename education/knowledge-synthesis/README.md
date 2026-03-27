---
name: knowledge-synthesis
description: "知識摘要與教材設計：呼叫 Claude API 對對話記錄產出摘要、重要度評分、複習素材。"
---

# Knowledge Synthesis

從 `personal/knowledge-base` 抽離的摘要與教材設計層。

## 來源
原始碼來自：`/data/personal/knowledge-base/scripts/summarize/`

## 職責

| 模組 | 說明 |
|------|------|
| `summarize.py` | 讀取 processed/ JSON → 呼叫 Claude API → 寫入 summaries/ |
| `prompt.py` | System prompt 設計：篩選規則、格式、重要度評分標準 |
| `writer.py` | 輸出 YAML + Markdown 摘要檔 |

## 輸入 / 輸出

- **輸入**：統一 schema JSON（來自 `intelligence/ai-chat-crawler`）
- **輸出**：`summaries/<source>/<id>.yml`（含摘要、標籤、重要度）

## 排程 / 核心分離

- **核心**：`summarize.py` 可直接呼叫，傳入輸入目錄與輸出目錄
- **排程 adapter**：待建立（呼叫核心 + 符合 operations/scheduling manifest 格式）

## 狀態
⬜ 待從 personal/knowledge-base 正式遷入
