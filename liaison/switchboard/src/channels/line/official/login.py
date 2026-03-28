# /// script
# dependencies = ["playwright", "qrcode[pil]", "zxing-cpp", "pillow"]
# ///
"""
login.py - LINE Developers Console 登入（QR code 掃描）

仿照個人帳號作法：canvas 解碼 → ASCII terminal + HTTP server 圖片

對外介面:
  ensure_logged_in(page, qr_port)  確認已登入，否則引導 QR 登入

直接執行（測試登入）:
  uv run login.py [--qr-port 8889]
"""
import asyncio, base64, http.server, io, re, socket, sys, threading
from playwright.async_api import Page
from PIL import Image
import zxingcpp
import qrcode as qrlib

_CONSOLE_URL = "https://developers.line.biz/console/"

# ── QR 取得（img element，access.line.me 使用 img 非 canvas）────────


async def _get_qr_png(page: Page) -> bytes | None:
    """等待 QR img 出現並截圖，回傳 PNG bytes"""
    try:
        el = await page.wait_for_selector("img", timeout=10000)
        return await el.screenshot(type="png")
    except Exception:
        return None


def _decode_qr(png: bytes) -> str | None:
    img = Image.open(io.BytesIO(png))
    for scale in (5, 3, 1):
        big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
        results = zxingcpp.read_barcodes(big)
        if results:
            return results[0].text
    return None


def _make_png(qr_url: str) -> bytes:
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


# ── HTTP server ────────────────────────────────────────────────────


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


# ── 登入狀態偵測 ──────────────────────────────────────────────────


async def _is_logged_in(page: Page) -> bool:
    try:
        await page.wait_for_selector(
            '[class*="UserInfo"], [class*="ProviderList"], '
            'a[href*="/console/channel"], [data-testid="user-avatar"]',
            timeout=5000,
        )
        return True
    except Exception:
        return False


async def _poll_until_done(page: Page, srv: http.server.HTTPServer) -> None:
    """輪詢：顯示確認號碼，等待回到 developers.line.biz（host 完整比對）"""
    from urllib.parse import urlparse
    prev_number = None
    while True:
        await asyncio.sleep(2)

        host = urlparse(page.url).hostname or ""
        if host == "developers.line.biz":
            srv.shutdown()
            print("\n>>> 登入成功！")
            return

        try:
            text = await page.inner_text("body")
            # 驗證碼為 4~6 位數字
            m = re.search(r'\b(\d{4,6})\b', text)
            if m and m.group(1) != prev_number:
                prev_number = m.group(1)
                print(f"\n┌────────────────────────────┐")
                print(f"│  確認號碼：  {prev_number:<6}      │")
                print(f"│  請在手機 LINE 上輸入確認  │")
                print(f"└────────────────────────────┘", flush=True)
        except Exception as e:
            print(f"[poll error] {e}", flush=True)


# ── QR 顯示與等待 ────────────────────────────────────────────────


async def _show_qr_and_wait(page: Page, qr_port: int) -> None:
    # 預設是 email/password，要切換到 QR code 登入
    # 用 text= 而非 button:has-text，因為元素可能是 div/a 而非 button
    try:
        await page.click('text=QR code login', timeout=5000)
        print(">>> 切換到 QR code 登入模式")
        await page.wait_for_selector("img", timeout=10000)
    except Exception as e:
        print(f">>> QR 切換失敗：{e}")

    qr_png = await _get_qr_png(page)
    qr_url = _decode_qr(qr_png) if qr_png else None

    if qr_url:
        _print_terminal(qr_url)
        png = _make_png(qr_url)
    else:
        await page.screenshot(path="/tmp/line-official-qr-page.png")
        print("（QR decode 失敗，截圖存於 /tmp/line-official-qr-page.png，改用截圖）")
        png = qr_png or b""

    srv = _serve(qr_port, png)
    ip = _local_ip()
    print(f"\n{'━' * 52}")
    print(f"  用 LINE app 掃描上方 QR code 登入")
    print(f"  備用圖片：http://{ip}:{qr_port}/")
    print(f"{'━' * 52}\n")
    await _poll_until_done(page, srv)


# ── 主函式 ────────────────────────────────────────────────────────


async def ensure_logged_in(page: Page, qr_port: int = 8889) -> None:
    await page.goto(_CONSOLE_URL, wait_until="networkidle", timeout=30000)
    print(f">>> 目前 URL：{page.url}")

    # 已登入：停在 developers.line.biz
    if "developers.line.biz" in page.url and "login" not in page.url:
        print(">>> 已登入 LINE Developers Console")
        return

    # 在 account.line.biz 登入頁：點 "LINE account" 進入 QR 流程
    if "account.line.biz" in page.url:
        print(">>> 點擊 LINE account...")
        await page.click('button:has-text("LINE account")', timeout=10000)
        await page.wait_for_load_state("networkidle")
        print(f">>> 跳轉後 URL：{page.url}")
        await _show_qr_and_wait(page, qr_port)
        return

    raise RuntimeError(f"未預期的頁面，請截圖確認：{page.url}")


if __name__ == "__main__":
    import argparse
    from playwright.async_api import async_playwright

    ap = argparse.ArgumentParser(description="LINE Developers Console 登入測試")
    ap.add_argument("--qr-port", type=int, default=8889)
    args = ap.parse_args()

    async def _run():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page    = await (await browser.new_context()).new_page()
            await ensure_logged_in(page, args.qr_port)
            print(f"目前 URL：{page.url}")
            await browser.close()

    asyncio.run(_run())
