---
name: price-comparison
description: "台灣電商比價爬蟲：PChome、蝦皮、原價屋，config-driven 採購清單，輸出 Markdown/HTML 報告。"
---

# Price Comparison Scraper

從 `personal/build-work-station` 抽離的比價爬蟲模組。

## 來源
原始碼來自：`/data/personal/build-work-station/scraper/`

## 職責

| 模組 | 說明 |
|------|------|
| `pchome.py` | PChome 24h API 封裝 |
| `shopee.py` | 蝦皮搜尋（需登入 session） |
| `coolpc.py` | 原價屋類別選項解析 |
| `shopee_login.py` + `browser.py` | Playwright 登入 & cookie 管理 |
| `config.py` | 採購清單、關鍵字、價格範圍配置 |
| `report.py` | 三來源結果彙整 → Markdown/HTML 報告 |

## 使用方式

```bash
# 1. 設定 config.py（採購清單）
# 2. 執行
bash run.sh
# 輸出至 report.md / report.html
```

## 狀態
⬜ 待從 personal/build-work-station 正式遷入
