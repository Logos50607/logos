# /// script
# dependencies = ["playwright", "qrcode[pil]", "zxing-cpp"]
# ///
"""
run.py - LINE 個人帳號登入主流程

用法:
  uv run run.py [--cdp http://localhost:9222] [--qr-port 8888]
"""

import argparse, asyncio, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import browser, extension, qr

SCRIPT_DIR = Path(__file__).parent
CDP_URL    = os.environ.get("LINE_PERSONAL_CDP_URL", "http://localhost:9222")
EXT_DIR    = SCRIPT_DIR / "ext"


async def main(cdp_url: str, qr_port: int) -> None:
    from playwright.async_api import async_playwright

    # 1. 確認瀏覽器已安裝
    browser.ensure_installed()

    # 2. 確認 LINE extension 已下載並注入 key
    extension.ensure_ready(EXT_DIR)

    # 3. 取得 extension ID
    ext_id = extension.get_id(EXT_DIR)

    # 4. 確認瀏覽器已啟動
    browser.ensure_running(cdp_url, EXT_DIR)

    # 5. 連接 CDP，開啟 LINE 登入頁面
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(cdp_url)
        ctx = b.contexts[0]
        line_page = next((pg for pg in ctx.pages if ext_id in pg.url), None)
        if not line_page:
            line_page = await ctx.new_page()
            try:
                await line_page.goto(
                    f"chrome-extension://{ext_id}/index.html",
                    wait_until="domcontentloaded", timeout=10000)
            except Exception:
                pass  # extension panel 頁面 goto 會被攔截但頁面仍會開啟

        # 6. 顯示 QR code，等待登入，印出確認號碼
        await qr.show_and_wait(line_page, qr_port)

    print("\n下一步：uv run capture.py --duration 60")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="LINE 個人帳號登入")
    ap.add_argument("--cdp", default=CDP_URL)
    ap.add_argument("--qr-port", type=int, default=8888)
    args = ap.parse_args()
    asyncio.run(main(args.cdp, args.qr_port))
