# /// script
# dependencies = ["playwright"]
# ///
"""
logout.py - LINE 個人帳號登出

用法:
  uv run logout.py [--cdp http://localhost:9222]
"""

import argparse, asyncio, os
from playwright.async_api import async_playwright

CDP_URL = os.environ.get("LINE_PERSONAL_CDP_URL", "http://localhost:9222")


async def main(cdp_url: str) -> None:
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(cdp_url)
        ctx = b.contexts[0]

        ext_page = next(
            (pg for pg in ctx.pages
             if "ophjlpahpchlmihnnnihgmmeilfjmjjc" in pg.url and "index.html" in pg.url),
            None)
        if not ext_page:
            print("LINE extension 頁面不存在"); return

        # 導覽到設定頁，找登出按鈕
        await ext_page.evaluate("location.hash = '#/more/settings'")
        await asyncio.sleep(1)

        clicked = await ext_page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button,a,[role="button"]'));
            const btn = btns.find(el => /log.?out|登出|sign.?out/i.test(el.textContent));
            if (btn) { btn.click(); return true; }
            return false;
        }""")

        if not clicked:
            print("找不到登出按鈕，直接清除 extension storage...")
            await ext_page.evaluate("""() => {
                chrome.storage.local.clear();
                chrome.storage.session?.clear();
            }""")
        else:
            # 確認登出彈窗
            await asyncio.sleep(1)
            await ext_page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const confirm = btns.find(el => /ok|confirm|yes|確認|登出/i.test(el.textContent));
                if (confirm) confirm.click();
            }""")

        await asyncio.sleep(1)
        await ext_page.reload()
        print("✓ 已登出，可重新跑 run.py 登入")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="LINE 個人帳號登出")
    ap.add_argument("--cdp", default=CDP_URL)
    args = ap.parse_args()
    asyncio.run(main(args.cdp))
