# /// script
# dependencies = ["playwright"]
# ///
"""
send_message.py - 透過 LINE extension UI 發送文字訊息

原理：
  1. 連接 CDP → 找到 LINE extension page
  2. 導航到聊天室（`#/chats/<to>`）
  3. 在 editor (contenteditable div) 輸入文字，按 Enter 送出
  4. Extension 自動處理 E2EE 加密（negotiateE2EEPublicKey + sendMessage）
  5. 發送後返回原始頁面

用法：
  uv run send_message.py --to <mid> --text "訊息內容"
  uv run send_message.py --to U1234... --text "Hi"
  uv run send_message.py --to C5678... --text "大家好"

注意：
  - 發送後該聊天室的訊息會被標記為已讀（sendChatChecked 觸發）
  - 送出後自動返回原始頁面
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. parse_args
# 2. send_text(page, to, text)  - UI 模擬
# 3. main

import argparse
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

_EXT_ID_FILE    = Path(__file__).parent / ".ext-id"
_EXT_ID_DEFAULT = "ophjlpahpchlmihnnnihgmmeilfjmjjc"

def _load_ext_id():
    if val := os.getenv("LINE_PERSONAL_EXT_ID"): return val
    if _EXT_ID_FILE.exists(): return _EXT_ID_FILE.read_text().strip()
    return _EXT_ID_DEFAULT

EXT_ID  = _load_ext_id()
CDP_URL = os.getenv("LINE_PERSONAL_CDP_URL", "http://localhost:9222")

EDITOR_SEL  = ".chatroomEditor-module__textarea__yKTlH"
CHATITEM_SEL = '[data-mid="{to}"]'


# ── 1. 參數 ───────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Send LINE message via UI")
    p.add_argument("--to",   required=True, help="目標 chat mid（U/C/R 開頭）")
    p.add_argument("--text", required=True, help="訊息內容")
    return p.parse_args()


# ── 2. 發送訊息 ───────────────────────────────────────────────────

async def send_text(page, to: str, text: str) -> dict:
    """返回 {ok: True} 或 {error: str}"""
    original_url = page.url

    # 監控 sendMessage 請求確認送出
    sent = {}
    async def on_req(req):
        if 'sendMessage' in req.url and 'line-chrome-gw' in req.url:
            sent['url'] = req.url

    page.on('request', on_req)

    try:
        # 導航到聊天清單，等聊天項目出現
        await page.evaluate("window.location.hash = '#/chats'")
        await asyncio.sleep(1)

        sel = CHATITEM_SEL.format(to=to)

        # 嘗試1：直接點擊（已在畫面內）
        try:
            await page.click(sel, timeout=2000)
        except Exception:
            # 嘗試2：滾動聊天清單直到找到 data-mid 元素
            list_sel = "ul[class*='chatlist'], div[class*='chatList'], div[class*='chat_list']"
            scrolled = await page.evaluate(f'''(async (to) => {{
                const sel = `[data-mid="${{to}}"]`;
                const lists = document.querySelectorAll("ul, div[class*=chatlist], div[class*=chat_list]");
                // 滾動有 overflow 的容器
                for (const el of document.querySelectorAll("*")) {{
                    const s = window.getComputedStyle(el);
                    if ((s.overflowY === "auto" || s.overflowY === "scroll") && el.scrollHeight > el.clientHeight) {{
                        for (let i = 0; i < 30; i++) {{
                            if (document.querySelector(sel)) return true;
                            el.scrollBy(0, 200);
                            await new Promise(r => setTimeout(r, 150));
                        }}
                    }}
                }}
                return !!document.querySelector(sel);
            }})''', to)

            try:
                await page.click(sel, timeout=3000)
            except Exception as e:
                return {'error': f"找不到聊天室 {to[:20]}：{e}"}

        await asyncio.sleep(1.5)

        # 等 editor 出現並輸入
        try:
            editor = page.locator(EDITOR_SEL)
            await editor.wait_for(timeout=8000)
            await editor.click()
            await page.keyboard.type(text)
            await asyncio.sleep(0.3)
            await page.keyboard.press("Enter")
        except Exception as e:
            return {'error': f"Editor 操作失敗：{e}"}

        # 等 sendMessage request 觸發（最多 5 秒）
        for _ in range(50):
            if 'url' in sent:
                break
            await asyncio.sleep(0.1)

        if 'url' not in sent:
            return {'error': 'sendMessage request 未觸發，可能送出失敗'}

        return {'ok': True}

    finally:
        page.remove_listener('request', on_req)
        # 返回原始頁面
        if original_url != page.url:
            await page.evaluate(f"window.location.href = {repr(original_url)}")
            await asyncio.sleep(0.5)


# ── 3. 主程式 ─────────────────────────────────────────────────────

async def main():
    args = parse_args()

    async with async_playwright() as p:
        print(f">>> 連接 CDP: {CDP_URL}", flush=True)
        b = await p.chromium.connect_over_cdp(CDP_URL)
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


asyncio.run(main())
