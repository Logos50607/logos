---
task_name: liaison-line-personal-sync
description: "確保 LINE 個人帳號的 sync.py（訊息同步 daemon）與 media_server.py（媒體 HTTP server）持續執行；若任一服務不在執行則自動重啟。"
owner_group: liaison
owner_project: switchboard
schedule:
  type: interval
  expr: "5m"
command:
  type: script
  script_path: scripts/ensure-services.sh
  working_dir: /data/personal/line-personal
retry:
  max_attempts: 2
  delay_seconds: 30
failure:
  notify: escalate
  fallback: "手動執行 scripts/ensure-services.sh 並查看 logs/sync.log"
report:
  format: markdown
  destination: ""
enabled: true
---

## 背景說明

`sync.py` 是 LINE 個人帳號的核心背景 daemon：
- 每 5 秒（TUI 開啟時）或 10 分鐘（閒置時）輪詢
- 處理 outbox（發送訊息）、抓新訊息、E2EE 解密、同步聯絡人、下載媒體佇列

`webapp/media_server.py` 提供媒體 HTTP server（port 8889），讓使用者透過 SSH tunnel 下載 E2EE 加密的圖片/影片/音訊/檔案。

## 前置條件

- Chrome 已登入 LINE extension（`run.py` 完成登入流程）
- CDP 可連（`http://localhost:9222`）

## 注意事項

- 本服務不應在 Chrome 未登入時啟動，否則會持續失敗
- `logs/sync.log` 與 `logs/media-server.log` 為主要 debug 來源
