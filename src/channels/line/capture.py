"""
capture.py - 錄製 LINE Web 的 HTTP + WebSocket 流量
用法: python capture.py [--duration 60]

第一次執行：瀏覽器會開啟，掃 QR 登入後按 Enter 繼續錄製
之後執行：自動帶入 session，無需登入
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

SESSION_FILE = Path(__file__).parent / "session" / "state.json"
OUTPUT_FILE  = Path(__file__).parent / "captured.json"
LINE_URL     = "https://chat.line.me"
DURATION     = int(sys.argv[sys.argv.index("--duration") + 1]) if "--duration" in sys.argv else 60


def _try_decode(payload):
    """嘗試將 WS payload 解析為 JSON，失敗則回傳 hex"""
    if isinstance(payload, bytes):
        try:    return json.loads(payload.decode("utf-8"))
        except: return payload.hex()
    try:    return json.loads(payload)
    except: return payload


async def record(page, log: list):
    """掛載 HTTP response 與 WebSocket 攔截器"""

    async def on_response(response):
        try:
            body = await response.body()
            decoded = _try_decode(body)
        except:
            decoded = None
        log.append({
            "type": "http",
            "ts": time.time(),
            "method": response.request.method,
            "url": response.url,
            "status": response.status,
            "body": decoded,
        })

    def on_websocket(ws):
        def on_recv(payload):
            log.append({"type": "ws_recv", "ts": time.time(), "url": ws.url, "data": _try_decode(payload)})
        def on_send(payload):
            log.append({"type": "ws_send", "ts": time.time(), "url": ws.url, "data": _try_decode(payload)})
        ws.on("framereceived", lambda f: on_recv(f["payload"]))
        ws.on("framesent",     lambda f: on_send(f["payload"]))

    page.on("response",  on_response)
    page.on("websocket", on_websocket)


async def main():
    log = []
    first_run = not SESSION_FILE.exists()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx_args = {} if first_run else {"storage_state": str(SESSION_FILE)}
        ctx  = await browser.new_context(**ctx_args)
        page = await ctx.new_page()

        await record(page, log)
        await page.goto(LINE_URL)

        if first_run:
            print(">>> 請在瀏覽器中掃描 QR Code 登入，登入完成後按 Enter...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            await ctx.storage_state(path=str(SESSION_FILE))
            print(f">>> Session 已儲存至 {SESSION_FILE}")

        print(f">>> 錄製中（{DURATION} 秒），請勿點入任何對話視窗...")
        await asyncio.sleep(DURATION)

        OUTPUT_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))
        print(f">>> 完成！共 {len(log)} 筆紀錄，已儲存至 {OUTPUT_FILE}")
        await browser.close()


asyncio.run(main())
