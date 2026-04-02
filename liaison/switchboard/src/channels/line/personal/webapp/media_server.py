# /// script
# dependencies = []
# ///
"""
media_server.py - LINE E2EE 媒體下載 HTTP server (預設 port 8889)

GET /          → 所有媒體訊息 HTML 列表（含下載連結）
GET /<msg_id>  → 下載解密後的媒體（首次觸發 sync.py 解密，快取後即時）

SSH tunnel 用法：
  ssh -L 8889:localhost:8889 user@server
  # 再用本地瀏覽器開 http://localhost:8889/

啟動：uv run webapp/media_server.py [--port 8889]
"""

# 目錄:
# 1. 常數 & 輔助函式（_load_messages / _find_msg / _content_info / _enqueue）
# 2. MediaHandler（do_GET / _index / _media / _send）
# 3. main()

import json, mimetypes, time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

DATA  = Path(__file__).parent.parent / "data"
MEDIA = DATA / "media"
PORT  = 8889

_CT_LABEL = {1: ("image/jpeg", ".jpg"), 2: ("video/mp4", ".mp4"),
             3: ("audio/mp4", ".m4a"), 14: ("application/octet-stream", "")}
_CT_ICON  = {1: "📷 圖片", 2: "🎬 影片", 3: "🎵 音訊", 14: "📎 檔案"}


# ── 1. 輔助函式 ──────────────────────────────────────────────────

def _load_messages() -> dict:
    p = DATA / "messages.json"
    return json.loads(p.read_text()) if p.exists() else {}

def _find_msg(msg_id: str) -> dict | None:
    for chat in _load_messages().values():
        for m in chat:
            if isinstance(m, dict) and m.get("id") == msg_id:
                return m
    return None

def _load_contacts() -> dict:
    c: dict = {}
    for f in (DATA / "friends.json", DATA / "groups.json"):
        if f.exists():
            c.update(json.loads(f.read_text()))
    return c

def _content_info(message: dict) -> tuple[str, str]:
    ct   = int(message.get("contentType", 0))
    meta = message.get("contentMetadata") or {}
    if ct == 14:
        fname = meta.get("FILE_NAME", f"{message['id']}.bin")
        mime, _ = mimetypes.guess_type(fname)
        return mime or "application/octet-stream", fname
    mime, ext = _CT_LABEL.get(ct, ("application/octet-stream", ""))
    return mime, f"{message['id']}{ext}"

def _enqueue(msg_id: str) -> None:
    """將 msg_id 寫入 download_queue.json（已存在則跳過）。"""
    MEDIA.mkdir(parents=True, exist_ok=True)
    q_path = DATA / "download_queue.json"
    try:
        q = json.loads(q_path.read_text()) if q_path.exists() else []
    except Exception:
        q = []
    if not any(item.get("msg_id") == msg_id for item in q):
        q.append({"msg_id": msg_id, "status": "pending"})
        q_path.write_text(json.dumps(q, ensure_ascii=False))


# ── 2. HTTP Handler ──────────────────────────────────────────────

class MediaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(self.path.lstrip("/").split("?")[0])
        if not path:
            self._index()
        else:
            self._media(path)

    def _index(self):
        msgs     = _load_messages()
        contacts = _load_contacts()
        rows = []
        for mid, chat in msgs.items():
            name = contacts.get(mid, mid[:16])
            for m in sorted(chat, key=lambda x: int(x.get("createdTime", 0)), reverse=True):
                ct = int(m.get("contentType", 0))
                if ct not in _CT_LABEL or not m.get("chunks"):
                    continue
                ts   = int(m.get("createdTime", 0)) // 1000
                dt   = datetime.fromtimestamp(ts).strftime("%m/%d %H:%M") if ts else ""
                meta = m.get("contentMetadata") or {}
                desc = meta.get("FILE_NAME", "") or _CT_ICON.get(ct, "")
                done = "✅ " if (MEDIA / m["id"]).exists() else ""
                rows.append(
                    f'<tr><td>{dt}</td><td>{name}</td>'
                    f'<td>{desc}</td>'
                    f'<td>{done}<a href="/{m["id"]}">下載</a></td></tr>'
                )
        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"><title>LINE 媒體</title>'
            '<style>body{font-family:sans-serif;padding:16px}'
            'table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}'
            'a{color:#0066cc}</style></head><body>'
            f'<h2>LINE 媒體（共 {len(rows)} 筆）</h2>'
            '<table><tr><th>時間</th><th>聯絡人</th><th>檔案</th><th>下載</th></tr>'
            + "".join(rows)
            + "</table></body></html>"
        )
        self._send(200, "text/html; charset=utf-8", html.encode())

    def _media(self, msg_id: str):
        cached = MEDIA / msg_id
        if not cached.exists():
            msg = _find_msg(msg_id)
            if not msg:
                self.send_error(404, "Message not found")
                return
            _enqueue(msg_id)
            for _ in range(60):   # 最多等 60 秒
                time.sleep(1)
                if cached.exists():
                    break
            if not cached.exists():
                self.send_error(503, "Download timed out (sync.py running?)")
                return
        msg  = _find_msg(msg_id)
        mime, fname = _content_info(msg) if msg else ("application/octet-stream", msg_id)
        data = cached.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
        self.end_headers()
        self.wfile.write(data)

    def _send(self, code: int, ct: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass   # 不印 access log


# ── 3. 主程式 ────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="LINE 媒體下載 HTTP server")
    p.add_argument("--port", type=int, default=PORT, help="監聽 port（預設 8889）")
    args = p.parse_args()
    MEDIA.mkdir(parents=True, exist_ok=True)
    print(f"媒體 server 啟動：http://localhost:{args.port}/")
    print(f"SSH tunnel：ssh -L {args.port}:localhost:{args.port} user@server")
    ThreadingHTTPServer(("0.0.0.0", args.port), MediaHandler).serve_forever()


if __name__ == "__main__":
    main()
