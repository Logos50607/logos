"""
qr.py - LINE QR code 取得、顯示與登入狀態監聽

對外介面:
  show_and_wait(page, qr_port)  顯示 QR code，等待登入，印出確認號碼
"""

import asyncio, http.server, io, json, socket, sys, threading
from playwright.async_api import Page
import qrcode as qrlib


_QR_URL_TEMPLATE = "https://liff.line.me/login-auth/qr?authSessionId={}"
_QR_API_PATH     = "createS"   # LINE GW endpoint 含此字串


# ── QR data 取得（攔截 network response）────────────────────────

async def _fetch_auth_session_id(page: Page) -> str | None:
    """點 refresh，攔截 LINE GW response，回傳 authSessionId"""
    future: asyncio.Future = asyncio.get_event_loop().create_future()

    async def on_response(resp):
        if future.done(): return
        if _QR_API_PATH not in resp.url: return
        try:
            body = await resp.body()
            data = json.loads(body)
            sid = data.get("data", {}).get("authSessionId")
            if sid:
                future.set_result(sid)
        except Exception:
            pass

    page.on("response", on_response)
    await page.evaluate("""() => {
        document.querySelector('[class*="button_refresh"]')?.click();
    }""")
    try:
        return await asyncio.wait_for(future, timeout=15)
    except asyncio.TimeoutError:
        return None
    finally:
        page.remove_listener("response", on_response)


def _make_png(qr_url: str) -> bytes:
    """從 URL 生成 QR code PNG bytes"""
    qr = qrlib.QRCode(border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _print_terminal(qr_url: str) -> None:
    qr = qrlib.QRCode(border=1)
    qr.add_data(qr_url)
    qr.make(fit=True)
    try:
        qr.print_ascii(invert=True, tty=True)
    except OSError:
        qr.print_ascii(invert=True)


# ── HTTP server ──────────────────────────────────────────────────

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
    import subprocess, os, signal
    r = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True)
    for pid in r.stdout.split():
        try: os.kill(int(pid), signal.SIGTERM)
        except Exception: pass


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


def _local_ip() -> str:
    for target in ("10.255.255.255", "192.168.1.1", "172.16.0.1"):
        try:
            s = socket.socket(); s.settimeout(1); s.connect((target, 1))
            ip = s.getsockname()[0]; s.close()
            if not ip.startswith("127."): return ip
        except Exception: pass
    try: return socket.gethostbyname(socket.gethostname())
    except Exception: return "localhost"


# ── 登入狀態偵測 ─────────────────────────────────────────────────

async def _state(page: Page) -> tuple[str, str | None]:
    """回傳 (state, number)  state: 'menu'|'qr'|'number'|'done'|'unknown'"""
    try:
        r = await page.evaluate("""() => {
            const text = document.body?.innerText || '';
            if (document.querySelector('[class*="chatList"],[class*="conversationList"]'))
                return ['done', null];
            if (!document.querySelector('canvas')) {
                const m = text.match(/(?:^|\\s)(\\d{6})(?:\\s|$)/m);
                if (m && document.querySelector('[class*="loginPage"]'))
                    return ['number', m[1]];
            }
            if (document.querySelector('canvas'))
                return ['qr', null];
            if (document.querySelector('[class*="loginPage"]'))
                return ['menu', null];
            return ['unknown', null];
        }""")
        return r[0], r[1]
    except Exception:
        return 'unknown', None


# ── 等待就緒 ─────────────────────────────────────────────────────

async def _wait_for_login_page(page: Page) -> str:
    """等登入頁或已登入，回傳最終 state"""
    await page.wait_for_selector(
        '[class*="loginPage"],[class*="chatList"],[class*="conversationList"]',
        timeout=15000)
    state, _ = await _state(page)
    return state


# ── 顯示 QR ──────────────────────────────────────────────────────

async def _display_qr(page: Page, qr_port: int) -> http.server.HTTPServer:
    """攔截 QR session ID，顯示 QR，等使用者按 Enter"""
    sid = await _fetch_auth_session_id(page)
    if not sid:
        print("（無法取得 QR session ID）")
        srv = _serve(qr_port, b"")
    else:
        qr_url = _QR_URL_TEMPLATE.format(sid)
        _print_terminal(qr_url)
        png = _make_png(qr_url)
        srv = _serve(qr_port, png)

    ip = _local_ip()
    print(f"\n{'━' * 45}")
    print(f"  用手機掃描上方 QR code 登入 LINE")
    print(f"  備用圖片：http://{ip}:{qr_port}/")
    print(f"{'━' * 45}", flush=True)
    print("\n掃描完成後按 Enter...", flush=True)
    await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
    return srv


# ── 輪詢直到登入完成 ──────────────────────────────────────────────

async def _poll_until_done(page: Page, srv: http.server.HTTPServer) -> None:
    prev = "qr"
    while True:
        await asyncio.sleep(2)
        state, number = await _state(page)
        if state == "number" and prev != "number":
            print(f"\n┌──────────────────────────┐")
            print(f"│  確認號碼：  {number}     │")
            print(f"│  在手機上點確認           │")
            print(f"└──────────────────────────┘", flush=True)
        elif state == "done":
            print("\n✓ 登入成功！")
            srv.shutdown()
            return
        prev = state


# ── 主函式 ───────────────────────────────────────────────────────

async def show_and_wait(page: Page, qr_port: int) -> None:
    state = await _wait_for_login_page(page)
    if state == "done":
        print("✓ 已登入")
        return
    srv = await _display_qr(page, qr_port)
    await _poll_until_done(page, srv)
