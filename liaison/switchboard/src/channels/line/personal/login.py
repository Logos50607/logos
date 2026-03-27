# /// script
# dependencies = ["playwright", "pillow", "zxing-cpp", "qrcode"]
# ///
"""
login.py - LINE 個人帳號登入流程

功能:
  1. 確認 Chrome + LINE extension 已就緒（否則提示執行 start.sh）
  2. 開啟 LINE 登入頁面
  3. 擷取 QR code，透過 HTTP 在本機提供給使用者掃描
  4. 等待掃描 → 顯示確認號碼（手機上也會出現，點一下確認即可）
  5. 登入成功後提示可執行 capture.py

用法:
  uv run login.py [--cdp http://localhost:9222] [--qr-port 8888]
"""

import argparse
import asyncio
import base64
import http.server
import io
import os
import sys
import threading
from pathlib import Path

import qrcode as qrlib
import zxingcpp
from PIL import Image
from playwright.async_api import async_playwright

EXT_ID = "ophjlpahpchlmihnnnihgmmeilfjmjjc"
SCRIPT_DIR = Path(__file__).parent


# ── HTTP server 供使用者開瀏覽器看 QR code ──────────────────────────

class _PNGHandler(http.server.BaseHTTPRequestHandler):
    png_bytes: bytes = b""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(self.__class__.png_bytes)))
        self.end_headers()
        self.wfile.write(self.__class__.png_bytes)

    def log_message(self, *_):
        pass  # 靜音


def _start_http(port: int, png_bytes: bytes) -> http.server.HTTPServer:
    _PNGHandler.png_bytes = png_bytes
    srv = http.server.HTTPServer(("0.0.0.0", port), _PNGHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ── QR code 擷取與顯示 ──────────────────────────────────────────────

async def _get_qr_png(page) -> bytes | None:
    """從 LINE 頁面的 canvas 擷取 QR code PNG"""
    data_url = await page.evaluate("""() => {
        const c = document.querySelector('canvas');
        return c ? c.toDataURL('image/png') : null;
    }""")
    if not data_url:
        return None
    return base64.b64decode(data_url.split(",")[1])


def _decode_qr(png_bytes: bytes) -> str | None:
    """解碼 QR code，回傳資料字串"""
    img = Image.open(io.BytesIO(png_bytes))
    img_big = img.resize((img.width * 3, img.height * 3), Image.NEAREST)
    results = zxingcpp.read_barcodes(img_big)
    return results[0].text if results else None


def _print_qr(qr_data: str) -> None:
    """在 terminal 顯示 QR code"""
    qr = qrlib.QRCode(border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


# ── 登入狀態偵測 ──────────────────────────────────────────────────

async def _login_state(page) -> dict:
    """回傳 {state: 'qr'|'number'|'done', number: str|None}"""
    try:
        return await page.evaluate("""() => {
            const body = document.body?.innerText || '';

            // 登入成功：出現聊天列表
            if (document.querySelector('[class*="chatList"], [class*="conversationList"]'))
                return {state: 'done', number: null};

            // 掃描後出現確認號碼（通常是 3 位數）
            const m = body.match(/\\b(\\d{2,3})\\b/);
            const hasVerify = document.querySelector('[class*="verify"], [class*="pincode"], [class*="number"]');
            if (hasVerify && m) return {state: 'number', number: m[1]};

            // 一般情境：用頁面標題 / class 判斷
            if (document.querySelector('[class*="loginPage"]'))
                return {state: 'qr', number: null};

            // 掃描後轉場中
            return {state: 'transition', number: null};
        }""")
    except Exception:
        return {"state": "unknown", "number": None}


# ── 主流程 ────────────────────────────────────────────────────────

async def run(cdp_url: str, qr_port: int) -> None:
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            print(f"✗ 無法連線 Chrome CDP ({cdp_url}): {e}")
            print("  請先執行: sh start.sh")
            sys.exit(1)

        ctx = browser.contexts[0]

        # 找或開啟 LINE 頁面
        line_page = next((pg for pg in ctx.pages if EXT_ID in pg.url), None)
        if not line_page:
            print("開啟 LINE extension 頁面...")
            line_page = await ctx.new_page()
            try:
                await line_page.goto(
                    f"chrome-extension://{EXT_ID}/index.html",
                    wait_until="domcontentloaded", timeout=10000)
            except Exception:
                pass

        # 等待登入頁面載入
        print("等待 LINE 登入頁面載入...", end="", flush=True)
        for _ in range(15):
            await asyncio.sleep(1)
            st = await _login_state(line_page)
            if st["state"] in ("qr", "number", "done"):
                break
            print(".", end="", flush=True)
        print()

        if st["state"] == "done":
            print("✓ 已登入，可直接執行 capture.py")
            await browser.close()
            return

        # 擷取 QR code
        qr_png = await _get_qr_png(line_page)
        if not qr_png:
            qr_png = await line_page.screenshot(full_page=False)

        # Terminal 顯示 QR code
        qr_data = _decode_qr(qr_png) if qr_png else None
        if qr_data:
            print()
            _print_qr(qr_data)
        else:
            print("（無法在 terminal 顯示 QR，請用瀏覽器掃描）")

        # 同時開 HTTP server 供備用
        srv = _start_http(qr_port, qr_png)
        import socket
        try:
            s = socket.socket(); s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]; s.close()
        except Exception:
            local_ip = "localhost"

        print()
        print("━" * 50)
        print("  用 LINE 手機掃描上方 QR code 登入")
        print(f"  （備用圖片：http://{local_ip}:{qr_port}/）")
        print("━" * 50)
        print()

        # 輪詢登入狀態
        prev_state = "qr"
        while True:
            await asyncio.sleep(2)

            # 更新 QR code（QR 有效期約 3 分鐘，自動輪替）
            try:
                new_png = await _get_qr_png(line_page)
                if new_png:
                    _PNGHandler.png_bytes = new_png
            except Exception:
                pass

            st = await _login_state(line_page)

            if st["state"] == "number" and prev_state != "number":
                print()
                print("━" * 50)
                print(f"  手機上出現數字請確認：  {st['number']}  ")
                print("━" * 50)

            elif st["state"] == "done":
                print()
                print("✓ 登入成功！")
                srv.shutdown()
                break

            elif st["state"] == "qr" and prev_state != "qr":
                print("（QR code 已更新，請重新整理瀏覽器）")

            prev_state = st["state"]

        print()
        print("下一步：")
        print("  uv run capture.py --duration 60")
        await browser.close()


def main():
    ap = argparse.ArgumentParser(description="LINE 登入流程")
    ap.add_argument("--cdp", default=os.getenv("LINE_PERSONAL_CDP_URL", "http://localhost:9222"))
    ap.add_argument("--qr-port", type=int, default=8888)
    args = ap.parse_args()
    asyncio.run(run(args.cdp, args.qr_port))


main()
