# /// script
# dependencies = ["playwright"]
# ///
"""
diagnose.py - 診斷 LINE extension 頁面狀態

用法:
  uv run diagnose.py [--cdp http://localhost:9222]
"""

import argparse, asyncio, os
from pathlib import Path

CDP_URL = os.environ.get("LINE_PERSONAL_CDP_URL", "http://localhost:9222")


async def main(cdp_url: str) -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(cdp_url)
        ctx = b.contexts[0]

        print("=== 所有頁面 ===")
        for pg in ctx.pages:
            print(" ", pg.url[:100])

        ext_page = next(
            (pg for pg in ctx.pages
             if "ophjlpahpchlmihnnnihgmmeilfjmjjc" in pg.url and "index.html" in pg.url),
            None,
        )
        if not ext_page:
            print("\nLINE index.html 頁面不存在")
            return

        print(f"\n=== 使用頁面 ===\n  {ext_page.url}")
        await asyncio.sleep(2)

        info = await ext_page.evaluate("""() => {
            const canvas = document.querySelector('canvas');
            const text = document.body?.innerText || '';
            const btns = Array.from(document.querySelectorAll('button,a,[role="button"]'))
                .map(el => el.textContent.trim()).filter(Boolean);
            return {
                url: location.href,
                hasCanvas: !!canvas,
                canvasSize: canvas ? `${canvas.width}x${canvas.height}` : null,
                bodySnip: text.slice(0, 300),
                buttons: btns,
                loginPage: !!document.querySelector('[class*=\"loginPage\"]'),
                verifyPage: !!document.querySelector('[class*=\"verify\"],[class*=\"pincode\"]'),
                chatList: !!document.querySelector('[class*=\"chatList\"],[class*=\"conversationList\"]'),
            };
        }""")

        print("\n=== 頁面狀態 ===")
        for k, v in info.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp", default=CDP_URL)
    args = ap.parse_args()
    asyncio.run(main(args.cdp))
