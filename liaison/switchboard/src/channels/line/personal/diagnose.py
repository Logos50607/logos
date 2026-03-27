# /// script
# dependencies = ["playwright"]
# ///
"""
diagnose.py - 診斷 LINE extension 頁面狀態與網路請求

用法:
  uv run diagnose.py [--cdp http://localhost:9222]
  uv run diagnose.py --sniff   # 攔截 network responses，找 QR token
"""

import argparse, asyncio, os
from playwright.async_api import async_playwright

CDP_URL = os.environ.get("LINE_PERSONAL_CDP_URL", "http://localhost:9222")


async def sniff_network(cdp_url: str) -> None:
    """攔截 extension page 的 network responses，印出可能含 QR token 的內容"""
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(cdp_url)
        ctx = b.contexts[0]
        ext_page = next(
            (pg for pg in ctx.pages if "ophjlpahpchlmihnnnihgmmeilfjmjjc" in pg.url and "index.html" in pg.url),
            None)
        if not ext_page:
            print("LINE index.html 不存在"); return

        print(f"監聽頁面：{ext_page.url}")
        print("點擊 refresh 觸發 QR 請求...\n")

        async def on_response(resp):
            try:
                if resp.status != 200: return
                body = await resp.body()
                text = body.decode("utf-8", errors="ignore")
                if len(text) < 10 or len(text) > 50000: return
                # 只印出看起來含 token / qr 的 response
                if any(k in text.lower() for k in ("qr", "token", "auth", "login", "session")):
                    print(f"[{resp.status}] {resp.url[:100]}")
                    print(f"  body: {text[:300]}\n")
            except Exception:
                pass

        ext_page.on("response", on_response)

        await ext_page.evaluate("""() => {
            document.querySelector('[class*="button_refresh"]')?.click();
        }""")

        print("等待 10 秒攔截 responses...")
        await asyncio.sleep(10)


async def inspect_page(cdp_url: str) -> None:
    """檢查 extension page 的當前 DOM 狀態"""
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(cdp_url)
        ctx = b.contexts[0]

        print("=== 所有頁面 ===")
        for pg in ctx.pages:
            print(" ", pg.url[:100])

        ext_page = next(
            (pg for pg in ctx.pages
             if "ophjlpahpchlmihnnnihgmmeilfjmjjc" in pg.url and "index.html" in pg.url),
            None)
        if not ext_page:
            print("\nLINE index.html 頁面不存在"); return

        print(f"\n=== 使用頁面 ===\n  {ext_page.url}")

        info = await ext_page.evaluate("""() => {
            const canvas = document.querySelector('canvas');
            const text = document.body?.innerText || '';
            const btns = Array.from(document.querySelectorAll('button,a,[role="button"]'))
                .map(el => el.textContent.trim()).filter(Boolean);
            const numEls = Array.from(document.querySelectorAll('*'))
                .filter(el => el.childElementCount === 0 && /^\\d{6}$/.test(el.textContent.trim()))
                .map(el => ({tag: el.tagName, cls: el.className, text: el.textContent.trim()}));
            return {
                url: location.href,
                hasCanvas: !!canvas,
                bodySnip: text.slice(0, 400),
                buttons: btns,
                sixDigitElements: numEls,
                allClasses: Array.from(new Set(
                    Array.from(document.querySelectorAll('[class]'))
                        .flatMap(el => el.className.split(' '))
                        .filter(c => c.length > 3)
                )).slice(0, 40),
            };
        }""")

        print("\n=== 頁面狀態 ===")
        for k, v in info.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp", default=CDP_URL)
    ap.add_argument("--sniff", action="store_true", help="攔截 network responses")
    args = ap.parse_args()
    if args.sniff:
        asyncio.run(sniff_network(args.cdp))
    else:
        asyncio.run(inspect_page(args.cdp))
