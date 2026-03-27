---
name: operations
description: "營運組：定期執行的固定任務，含排程基礎建設與任務回報。"
---

# 營運組 (Operations)

## 核心目標

負責所有需定期、自動化執行的固定任務：維護排程基礎建設、執行各組註冊的任務、產出結構化回報。

## 專案

| 專案 | 說明 |
|------|------|
| `scheduling/` | 排程基礎建設：任務 manifest 掃描、執行、失敗處理與回報產出 |

## 對接介面

- **註冊排程**：各組在自身 `.agent/schedules/<task>.manifest.md` 放置 manifest
- **回報輸出**：`scheduling/reports/YYYYMMDD/daily-summary.md` → 交聯絡組統整後發送人類
- **Escalate**：任務失敗時觸發聯絡組（待聯絡組回報統整就位後啟用）
