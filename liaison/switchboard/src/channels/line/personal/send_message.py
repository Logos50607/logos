# /// script
# dependencies = ["playwright"]
# ///
"""
send_message.py - 透過 LINE extension UI 發送文字訊息

原理：
  1. open_chat(page, to) 開啟目標聊天室
  2. 在 chatroomEditor (contenteditable) 輸入文字，按 Enter
  3. Extension 自動處理 E2EE（negotiateE2EEPublicKey + sendMessage）
  4. 確認 sendMessage request 後返回原始頁面

注意：發送會觸發 sendChatChecked，目標聊天室訊息標為已讀。

用法：
  uv run send_message.py --to <mid> --text "訊息內容"
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. send_text(page, to, text)
# 2. main

import argparse
import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from open_chat import open_chat, EXT_ID, CDP_URL

EDITOR_SEL = ".chatroomEditor-module__textarea__yKTlH"


# ── 1. 發送 ───────────────────────────────────────────────────────

async def send_text(page, to: str, text: str) -> dict:
    original_url = page.url

    sent = {}
    async def on_req(req):
        if 'sendMessage' in req.url and 'line-chrome-gw' in req.url:
            sent['ok'] = True
    page.on('request', on_req)

    try:
        result = await open_chat(page, to)
        if 'error' in result:
            return result

        await asyncio.sleep(1.5)

        try:
            editor = page.locator(EDITOR_SEL)
            await editor.wait_for(timeout=8000)
            await editor.click()
            await page.keyboard.type(text)
            await asyncio.sleep(0.3)
            await page.keyboard.press("Enter")
        except Exception as e:
            return {'error': f"Editor 操作失敗：{e}"}

        for _ in range(50):
            if sent:
                break
            await asyncio.sleep(0.1)

        if not sent:
            return {'error': 'sendMessage request 未觸發，可能送出失敗'}

        return {'ok': True}

    finally:
        page.remove_listener('request', on_req)
        if original_url != page.url:
            await page.evaluate(f"window.location.href = {repr(original_url)}")
            await asyncio.sleep(0.5)


# ── 2. 主程式 ─────────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Send LINE message via UI")
    p.add_argument("--to",   required=True, help="目標 chat mid（U/C/R 開頭）")
    p.add_argument("--text", required=True, help="訊息內容")
    args = p.parse_args()

    async with async_playwright() as pw:
        print(f">>> 連接 CDP: {CDP_URL}", flush=True)
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        ctx = b.contexts[0]
        page = next((pg for pg in ctx.pages if EXT_ID in pg.url), None)
        if not page:
            raise RuntimeError("找不到 LINE extension page，請先執行 run.py 登入")

        print(f">>> 發送訊息到 {args.to[:20]}...", flush=True)
        result = await send_text(page, args.to, args.text)

        if result.get('ok'):
            print(">>> 成功送出", flush=True)
        else:
            print(f">>> 失敗: {result['error']}", flush=True)

        try:
            await b.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
