"""
qr.py - LINE QR code 擷取、顯示與登入狀態監聽

對外介面:
  show_and_wait(page, qr_port)  顯示 QR code，等待登入，印出確認號碼
"""

import base64, http.server, io, socket, threading
from playwright.async_api import Page
from PIL import Image
import zxingcpp
import qrcode as qrlib


# ── QR code 擷取與顯示 ───────────────────────────────────────────

async def _get_qr_png(page: Page) -> bytes | None:
    data_url = await page.evaluate("""() => {
        const c = document.querySelector('[class*="thumbnail"] canvas, canvas');
        return c ? c.toDataURL('image/png') : null;
    }""")
    if not data_url:
        return None
    return base64.b64decode(data_url.split(",")[1])


def _decode(png: bytes) -> str | None:
    img = Image.open(io.BytesIO(png))
    big = img.resize((img.width * 3, img.height * 3), Image.NEAREST)
    results = zxingcpp.read_barcodes(big)
    return results[0].text if results else None


def _print_terminal(data: str) -> None:
    qr = qrlib.QRCode(border=1)
    qr.add_data(data)
    qr.make(fit=True)
    try:
        qr.print_ascii(invert=True, tty=True)   # 半格字元，佔空間較小
    except OSError:
        qr.print_ascii(invert=True)


def _local_ip() -> str:
    try:
        s = socket.socket(); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "localhost"


class _Handler(http.server.BaseHTTPRequestHandler):
    png: bytes = b""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(self.__class__.png)))
        self.end_headers()
        self.wfile.write(self.__class__.png)
    def log_message(self, *_): pass


class _ReuseServer(http.server.HTTPServer):
    allow_reuse_address = True


def _free_port(port: int) -> None:
    """若 port 已被佔用則嘗試 kill 占用的 process"""
    import subprocess
    r = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True)
    for pid in r.stdout.split():
        try:
            import os, signal
            os.kill(int(pid), signal.SIGTERM)
        except Exception:
            pass


def _serve(port: int, png: bytes) -> http.server.HTTPServer:
    _Handler.png = png
    try:
        srv = _ReuseServer(("0.0.0.0", port), _Handler)
    except OSError:
        _free_port(port)
        import time; time.sleep(1)
        srv = _ReuseServer(("0.0.0.0", port), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ── 登入狀態偵測 ─────────────────────────────────────────────────

async def _state(page: Page) -> tuple[str, str | None]:
    """回傳 (state, number)
    state: 'menu'|'qr'|'number'|'done'|'unknown'
      menu = 登入選單（尚未點 QR code login）
      qr   = QR code 已顯示（canvas 存在）
    """
    try:
        r = await page.evaluate("""() => {
            const text = document.body?.innerText || '';
            if (document.querySelector('[class*="chatList"],[class*="conversationList"]'))
                return ['done', null];
            const m = text.match(/\\b(\\d{2,3})\\b/);
            if (document.querySelector('[class*="verify"],[class*="pincode"]') && m)
                return ['number', m[1]];
            if (document.querySelector('canvas'))
                return ['qr', null];
            if (document.querySelector('[class*="loginPage"]'))
                return ['menu', null];
            return ['unknown', null];
        }""")
        return r[0], r[1]
    except Exception:
        return 'unknown', None


async def _trigger_qr(page: Page) -> None:
    """點擊 refresh 觸發 QR code 產生，等待 canvas 出現"""
    await page.evaluate("""() => {
        document.querySelector('[class*="button_refresh"]')?.click();
    }""")
    await page.wait_for_selector('[class*="thumbnail"] canvas', timeout=15000)


# ── 等待就緒 / 顯示 QR ──────────────────────────────────────────

async def _wait_for_login_page(page: Page) -> str:
    """等登入頁或已登入，回傳最終 state"""
    await page.wait_for_selector(
        '[class*="loginPage"],[class*="chatList"],[class*="conversationList"]',
        timeout=15000)
    state, _ = await _state(page)
    if state in ("menu", "qr"):
        await _trigger_qr(page)
        state = "qr"
    return state


async def _display_qr(page: Page, qr_port: int) -> http.server.HTTPServer:
    """擷取並顯示 QR code，回傳 HTTP server"""
    png = await _get_qr_png(page)
    qr_data = _decode(png) if png else None
    if qr_data:
        _print_terminal(qr_data)
    else:
        print("（無法在 terminal 顯示 QR）")
    srv = _serve(qr_port, png or b"")
    ip = _local_ip()
    print(f"\n{'━' * 45}")
    print(f"  用手機掃描上方 QR code 登入 LINE")
    print(f"  （若 QR 太大，請改掃這個網址的圖片）")
    print(f"  http://{ip}:{qr_port}/")
    print(f"{'━' * 45}")
    return srv


async def _poll_until_done(page: Page, srv: http.server.HTTPServer) -> None:
    """輪詢登入狀態直到完成（每 2 秒檢查一次）"""
    import asyncio
    prev = "qr"
    while True:
        await asyncio.sleep(2)
        state, number = await _state(page)

        if state == "number" and prev != "number":
            print(f"\n┌─────────────────────┐")
            print(f"│  確認號碼：  {number:>3}     │")
            print(f"│  在手機上點確認      │")
            print(f"└─────────────────────┘")
        elif state == "done":
            print("\n✓ 登入成功！")
            srv.shutdown()
            return
        elif state == "qr":
            # QR 可能已刷新，同步更新 HTTP server 的圖片
            try:
                new_png = await _get_qr_png(page)
                if new_png:
                    _Handler.png = new_png
            except Exception:
                pass

        prev = state


# ── 主函式 ───────────────────────────────────────────────────────

async def show_and_wait(page: Page, qr_port: int) -> None:
    state = await _wait_for_login_page(page)
    if state == "done":
        print("✓ 已登入")
        return
    srv = await _display_qr(page, qr_port)
    await _poll_until_done(page, srv)
