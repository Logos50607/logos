---
name: social-media-scraper
description: "社群媒體爬蟲：YouTube/Instagram/TikTok/通用網頁，含 URL pipeline 分類分派架構。"
---

# Social Media Scraper

從 `personal/thai-trip-2026` 抽離的通用社群媒體爬蟲框架。

## 來源
原始碼來自：`/data/personal/thai-trip-2026/scraper/sources/` 與 `scraper/url_pipeline/`

## 職責

| 模組 | 說明 |
|------|------|
| `sources/youtube.py` | yt-dlp 搜尋 + 下載音檔 + Whisper 轉字幕 |
| `sources/instagram.py` | hashtag 搜尋 + 貼文圖片/說明擷取 |
| `sources/tiktok.py` | TikTok 爬蟲 |
| `sources/web.py` | 通用 HTML 頁面爬蟲 |
| `url_pipeline/` | URL 分類 → 分派 → handler → 結果輸出 |
| `browser.py` | Playwright persistent context 登入管理 |

## 架構
URL 輸入 → `classify.py` → `dispatch.py` → 對應 handler → 結構化輸出

## 狀態
⬜ 待從 personal/thai-trip-2026 正式遷入
