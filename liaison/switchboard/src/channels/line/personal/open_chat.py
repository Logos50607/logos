# /// script
# dependencies = ["playwright"]
# ///
"""
open_chat.py - 在 LINE extension UI 開啟指定聊天室

原理：
  導航到 #/chats，直接點擊 data-mid；
  若不在畫面內，滾動聊天清單直到找到後點擊。

用法（standalone）：
  uv run open_chat.py --to <mid>
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. open_chat(page, to)   - 核心：導航 + 找到 + 點擊
# 2. main（standalone）

import argparse
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from gw_client import EXT_ID, CDP_URL


# ── 1. 核心函式 ───────────────────────────────────────────────────

async def open_chat(page, to: str) -> dict:
    """
    開啟指定 mid 的聊天室。
    返回 {ok: True} 或 {error: str}。
    """
    await page.evaluate("window.location.hash = '#/chats'")
    await asyncio.sleep(1.5)

    sel = f'[data-mid="{to}"]'

    # 滾動虛擬清單：重設至頂部，再以 Playwright mouse.wheel 驅動 React re-render
    container_info = await page.evaluate('''() => {
        for (const el of document.querySelectorAll("*")) {
            const s = window.getComputedStyle(el);
            if ((s.overflowY === "auto" || s.overflowY === "scroll")
                    && el.scrollHeight > el.clientHeight + 50) {
                el.scrollTop = 0;
                el.dispatchEvent(new Event("scroll", {bubbles: true}));
                const r = el.getBoundingClientRect();
                return {cx: r.left + r.width/2, cy: r.top + r.height/2};
            }
        }
        return null;
    }''')
    await asyncio.sleep(0.5)  # 等 React re-render 頂部

    found = await page.evaluate(f'!!document.querySelector(`[data-mid="{to}"]`)')
    if not found and container_info:
        cx, cy = container_info['cx'], container_info['cy']
        await page.mouse.move(cx, cy)
        for _ in range(60):
            if await page.evaluate(f'!!document.querySelector(`[data-mid="{to}"]`)'):
                found = True
                break
            await page.mouse.wheel(0, 200)
            await asyncio.sleep(0.12)

    if not found:
        return {'error': f"找不到聊天室 {to[:20]}"}

    await page.evaluate(f'document.querySelector(`[data-mid="{to}"]`)?.scrollIntoView({{block:"center"}})')
    await asyncio.sleep(0.3)

    try:
        await page.click(sel, timeout=3000)
        return {'ok': True}
    except Exception as e:
        return {'error': f"點擊聊天室失敗 {to[:20]}：{e}"}


# ── 2. Standalone ─────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Open LINE chat in extension UI")
    p.add_argument("--to", required=True, help="目標 chat mid")
    args = p.parse_args()

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        ctx = b.contexts[0]
        page = next((pg for pg in ctx.pages if EXT_ID in pg.url), None)
        if not page:
            raise RuntimeError("找不到 LINE extension page")
        result = await open_chat(page, args.to)
        print("結果:", result)
        try:
            await b.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
