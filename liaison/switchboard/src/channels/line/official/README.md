---
name: line-official-adapter
description: "LINE 官方帳號 channel adapter（薄層）：核心邏輯已遷移至 /data/personal/line-official/。"
---

# LINE 官方帳號 Channel Adapter

> **核心服務已遷移至 `/data/personal/line-official/`**
>
> 本目錄為 switchboard 的薄 adapter，負責將 line-official 服務的訊息
> 轉換為 switchboard 統一 Message schema。

## 核心服務

| 項目 | 位置 |
|------|------|
| 核心服務 | `/data/personal/line-official/` |
| 登入、設定精靈 | `uv run login.py` / `uv run setup.py` |
| 收發訊息 | `chat_client.py`（REST API 待建） |

詳細說明見 `/data/personal/line-official/README.md`。

## Adapter 待辦

- [ ] 建立薄 adapter：呼叫 line-official REST API，轉換為 switchboard Message schema
- [ ] 依賴 line-official 的 webhook server 完成後串接 inbound
