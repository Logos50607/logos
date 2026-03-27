# /// script
# dependencies = ["playwright"]
# ///
"""
capture.py - 透過 CDP 攔截 LINE extension service worker 的背景流量

用法:
  uv run capture.py [--duration 60] [--output /path/to/output.json]

前置: Chrome 需以 --remote-debugging-port 啟動，並登入 LINE extension
  啟動指令見 README.md

Secrets:
  本地模式（monorepo）: LINE_PERSONAL_CDP_URL 由 .env 提供
  交付模式: 設定 env var LINE_PERSONAL_CDP_URL（預設 http://localhost:9222）

注意: 不開 LINE UI（避免 sendChatChecked 標記已讀），只監聽 service worker
"""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext

_EXT_ID_FILE = Path(__file__).parent / ".ext-id"
_EXT_ID_DEFAULT = "ophjlpahpchlmihnnnihgmmeilfjmjjc"

def _load_ext_id() -> str:
    """優先序：env var > .ext-id（start.sh 寫入）> 預設（store ID）"""
    if val := os.getenv("LINE_PERSONAL_EXT_ID"):
        return val
    if _EXT_ID_FILE.exists():
        return _EXT_ID_FILE.read_text().strip()
    return _EXT_ID_DEFAULT

EXT_ID  = _load_ext_id()
CDP_URL = os.getenv("LINE_PERSONAL_CDP_URL", "http://localhost:9222")
LINE_GW = "line-chrome-gw.line-apps.com"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Capture LINE extension traffic via CDP")
    p.add_argument("--duration", type=int, default=60, help="錄製秒數（預設 60）")
    p.add_argument("--output", type=Path,
                   default=Path(__file__).parent / "captured.json",
                   help="輸出 JSON 路徑")
    return p.parse_args()


def _try_decode(payload):
    if isinstance(payload, bytes):
        try:
            return json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return payload.hex()
    try:
        return json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload


def attach_listeners(page, log: list, label: str) -> None:
    async def on_response(response):
        if LINE_GW not in response.url:
            return
        try:
            body = _try_decode(await response.body())
        except Exception as e:
            body = {"_capture_error": str(e)}
        try:
            req_headers = dict(await response.request.all_headers())
        except Exception:
            req_headers = {}
        log.append({
            "type": "http",
            "src": label,
            "ts": time.time(),
            "method": response.request.method,
            "url": response.url,
            "status": response.status,
            "req_headers": req_headers,
            "body": body,
        })

    page.on("response", on_response)


def _attach_sw_if_line(sw, log: list) -> None:
    if EXT_ID in sw.url:
        print(f">>> service worker: {sw.url}", flush=True)
        attach_listeners(sw, log, "sw")


async def capture(ctx: BrowserContext, duration: int, log: list) -> None:
    for page in ctx.pages:
        if EXT_ID in page.url:
            print(f">>> LINE 頁面: {page.url}", flush=True)
            attach_listeners(page, log, "ui_page")

    for sw in ctx.service_workers:
        _attach_sw_if_line(sw, log)

    ctx.on("page", lambda pg: attach_listeners(pg, log, "new_page"))
    ctx.on("serviceworker", lambda sw: _attach_sw_if_line(sw, log))

    print(f">>> 錄製中（{duration} 秒）...", flush=True)
    await asyncio.sleep(duration)


async def main() -> None:
    args = parse_args()
    log: list = []

    async with async_playwright() as p:
        print(f">>> 連接 Chrome CDP: {CDP_URL}", flush=True)
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        await capture(browser.contexts[0], args.duration, log)
        await browser.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(log, ensure_ascii=False, indent=2))
    print(f">>> 完成，{len(log)} 筆 → {args.output}", flush=True)


asyncio.run(main())
