# /// script
# dependencies = ["playwright"]
# ///
"""
capture.py - 透過 CDP 攔截 LINE extension service worker 的背景流量
用法: uv run capture.py [--duration 60]

前置: Chrome 需以 --remote-debugging-port=9222 啟動
啟動指令:
  CHROME_DATA=/data/Logos/switchboard/src/channels/line/session/chrome-data
  flatpak run com.google.Chrome --remote-debugging-port=9222
    --user-data-dir=$CHROME_DATA --profile-directory="Profile 1"

注意: 不開 LINE UI（避免 sendChatChecked 標記已讀），只監聽 service worker
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

EXT_ID      = "ophjlpahpchlmihnnnihgmmeilfjmjjc"
CDP_URL     = "http://localhost:9222"
OUTPUT_FILE = Path(__file__).parent / "captured.json"
DURATION    = int(sys.argv[sys.argv.index("--duration") + 1]) if "--duration" in sys.argv else 60


def _try_decode(payload):
    if isinstance(payload, bytes):
        try:    return json.loads(payload.decode("utf-8"))
        except: return payload.hex()
    try:    return json.loads(payload)
    except: return payload


def attach_listeners(page, log: list, label: str = "page"):
    async def on_response(response):
        if "line-chrome-gw.line-apps.com" not in response.url:
            return
        try:
            body = _try_decode(await response.body())
        except:
            body = None
        try:
            req_headers = dict(await response.request.all_headers())
        except:
            req_headers = {}
        log.append({
            "type": "http", "src": label, "ts": time.time(),
            "method": response.request.method,
            "url": response.url,
            "status": response.status,
            "req_headers": req_headers,
            "body": body,
        })

    page.on("response", on_response)


async def main():
    log = []

    async with async_playwright() as p:
        print(f">>> 連接 Chrome CDP: {CDP_URL}", flush=True)
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0]

        # 攔截所有現有 page（不主動開新視窗，避免觸發 sendChatChecked）
        for page in ctx.pages:
            if EXT_ID in page.url:
                print(f">>> 偵測到已開啟的 LINE 頁面: {page.url}", flush=True)
                attach_listeners(page, log, "ui_page")

        # 監聽 service worker
        for sw in ctx.service_workers:
            if EXT_ID in sw.url:
                print(f">>> 監聽 service worker: {sw.url}", flush=True)
                attach_listeners(sw, log, "sw")

        # 監聽未來新開的 page / sw
        ctx.on("page", lambda pg: attach_listeners(pg, log, "new_page"))
        ctx.on("serviceworker", lambda sw: (
            print(f">>> 新 service worker: {sw.url}", flush=True) or
            attach_listeners(sw, log, "sw") if EXT_ID in sw.url else None
        ))

        print(f">>> 錄製中（{DURATION} 秒），不開 LINE UI...", flush=True)
        await asyncio.sleep(DURATION)

        OUTPUT_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))
        print(f">>> 完成！共 {len(log)} 筆，已儲存至 {OUTPUT_FILE}", flush=True)
        await browser.close()


asyncio.run(main())
