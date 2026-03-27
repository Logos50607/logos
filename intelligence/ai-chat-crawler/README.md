---
name: ai-chat-crawler
description: "AI 對話爬蟲：ChatGPT/Claude/Gemini 三平台原始對話擷取，輸出統一 schema。"
---

# AI Chat Crawler

從 `personal/knowledge-base` 抽離的 AI 對話爬蟲層。

## 來源
原始碼來自：`/data/personal/knowledge-base/scripts/crawlers/` 與 `scripts/parse/`

## 職責

| 模組 | 說明 |
|------|------|
| `crawlers/fetch_chatgpt.py` | ChatGPT `/backend-api` 全量對話擷取 |
| `crawlers/fetch_claude.py` | Claude `/api/organizations/{org_id}/chat_conversations` |
| `crawlers/fetch_gemini.py` | Gemini rpcid 動態偵測 + batchexecute 解析 |
| `crawlers/auth.py` | Playwright persistent context 登入管理 |
| `parse/schema.py` | 統一資料結構：`Conversation`, `Message` |
| `parse/parse_*.py` | 各平台 raw JSON → 統一 schema |

## 輸出格式

```json
{
  "id": "...",
  "source": "chatgpt|claude|gemini",
  "title": "...",
  "messages": [{"role": "user|assistant", "content": "..."}],
  "metadata": {}
}
```

## 狀態
⬜ 待從 personal/knowledge-base 正式遷入
