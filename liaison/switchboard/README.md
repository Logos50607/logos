---
name: switchboard
description: "聯絡組訊息工具入口：LINE 個人帳號與官方帳號的使用指南。"
---

# Switchboard

聯絡組對外聯繫的工具入口。目前包含兩個 LINE channel，各自為獨立服務，透過 symlink 指向 `/data/personal/`。

```
switchboard/
├── line-personal/  → /data/personal/line-personal   CDP + PostgreSQL + FastAPI :8000
└── line-official/  → /data/personal/line-official   Playwright + PostgreSQL + FastAPI :8001
```

---

## LINE 個人帳號（line-personal）

透過 Chrome CDP 掛接 LINE extension，不觸發已讀。

**啟動服務**

```bash
cd /data/personal/line-personal
podman-compose up -d
```

**每日使用**

```bash
# 確保服務在跑
bash scripts/ensure-services.sh

# 開 TUI 聊天介面
uv run webapp/tui.py

# 媒體 SSH tunnel（在本機）
ssh -L 8889:localhost:8889 user@server
# 瀏覽器開 http://localhost:8889/
```

**發送訊息**

```bash
# 文字（不觸發已讀）
uv run send_api.py --to <mid> --text "訊息"

# 圖片 / 影片 / 音訊 / 檔案
uv run send_image.py  --to <mid> --file image.png
uv run send_video.py  --to <mid> --file video.mp4
uv run send_audio.py  --to <mid> --file audio.m4a
uv run send_file.py   --to <mid> --file document.pdf

# 收回訊息
uv run send_api.py --unsend <msg_id>
```

**HTTP API（:8000）**

```bash
GET  /messages          # 取得訊息
GET  /auth/status       # 登入狀態
GET  /auth/qr           # 取得 QR code（未登入時）
```

詳細文件：`/data/personal/line-personal/README.md`

---

## LINE 官方帳號（line-official）

透過 Playwright 爬蟲輪詢 chat.line.biz，訊息持久化至 PostgreSQL。

**First-time setup**

```bash
cd /data/personal/line-official

uv sync
uv run playwright install chromium

# 登入（掃 QR code）
uv run login.py

# 啟動服務
docker-compose up -d
```

**HTTP API（:8001）**

```bash
# 查詢聊天室
curl http://localhost:8001/chats

# 查詢訊息
curl "http://localhost:8001/chats/<chatId>/messages?limit=20"

# 發送文字
curl -X POST http://localhost:8001/chats/<chatId>/messages \
     -H "Content-Type: application/json" \
     -d '{"text": "訊息內容"}'

# 發送圖片
curl -X POST http://localhost:8001/chats/<chatId>/media \
     -F "file=@/path/to/image.jpg"

# 查看 daemon 狀態
curl http://localhost:8001/health
```

詳細文件：`/data/personal/line-official/README.md`
