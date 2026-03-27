# /// script
# dependencies = ["playwright"]
# ///
"""
capture.py - 透過 CDP 攔截 LINE extension service worker 的背景流量

模式:
  fetch   先 reload extension 觸發 initial sync，安靜後結束（預設）
  listen  持續監聽，每筆訊息即時寫入 JSONL
  watch   同 listen，但印到 stdout（測試用）

用法:
  uv run capture.py                          # fetch 模式（預設）
  uv run capture.py fetch [--since DATE]     # 抓 DATE 之後的訊息
  uv run capture.py listen [--output FILE]   # 背景持續監聽
  uv run capture.py watch                    # 印到 stdout 看即時流量
"""

import argparse, asyncio, json, os, sys, time
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext

_EXT_ID_FILE    = Path(__file__).parent / ".ext-id"
_EXT_ID_DEFAULT = "ophjlpahpchlmihnnnihgmmeilfjmjjc"

def _load_ext_id() -> str:
    if val := os.getenv("LINE_PERSONAL_EXT_ID"): return val
    if _EXT_ID_FILE.exists(): return _EXT_ID_FILE.read_text().strip()
    return _EXT_ID_DEFAULT

EXT_ID  = _load_ext_id()
CDP_URL = os.getenv("LINE_PERSONAL_CDP_URL", "http://localhost:9222")
LINE_GW = "line-chrome-gw.line-apps.com"


# ── 解析 ─────────────────────────────────────────────────────────

def _try_decode(payload):
    if isinstance(payload, bytes):
        try: return json.loads(payload.decode("utf-8"))
        except Exception: return payload.hex()
    try: return json.loads(payload)
    except Exception: return payload


# ── 監聽附加 ─────────────────────────────────────────────────────

def attach_listeners(target, on_record, label: str) -> None:
    async def on_response(response):
        if LINE_GW not in response.url: return
        try:
            body = _try_decode(await response.body())
        except Exception as e:
            if "closed" in str(e).lower(): return
            body = {"_capture_error": str(e)}
        try:
            req_headers = dict(await response.request.all_headers())
        except Exception:
            req_headers = {}
        record = {
            "type": "http", "src": label,
            "ts": time.time(),
            "method": response.request.method,
            "url": response.url,
            "status": response.status,
            "req_headers": req_headers,
            "body": body,
        }
        await on_record(record)
    target.on("response", on_response)


def attach_all(ctx: BrowserContext, on_record) -> None:
    for page in ctx.pages:
        if EXT_ID in page.url:
            attach_listeners(page, on_record, "ui_page")
    for sw in ctx.service_workers:
        if EXT_ID in sw.url:
            print(f">>> service worker: {sw.url}", flush=True)
            attach_listeners(sw, on_record, "sw")
    ctx.on("serviceworker", lambda sw: (
        attach_listeners(sw, on_record, "sw")
        if EXT_ID in sw.url else None
    ))


# ── 模式實作 ──────────────────────────────────────────────────────

async def mode_fetch(ctx: BrowserContext, output: Path, since: float | None) -> None:
    """reload extension，等 initial sync 完成後寫檔"""
    log = []
    idle_since = [time.time()]

    async def on_record(r):
        if since and r["ts"] < since: return
        log.append(r)
        idle_since[0] = time.time()
        print(f"  [{len(log)}] {r['url'].split('/')[-1]}", flush=True)

    attach_all(ctx, on_record)

    # reload extension page 觸發 initial sync
    ext_page = next((pg for pg in ctx.pages if EXT_ID in pg.url), None)
    if ext_page:
        print(">>> reload extension 觸發 sync...", flush=True)
        await ext_page.reload()
    else:
        print(">>> extension page 不存在，等待流量...", flush=True)

    # 等到 5 秒沒有新流量才結束
    print(">>> 等待 sync 完成（5 秒無流量後結束）...", flush=True)
    while True:
        await asyncio.sleep(1)
        if time.time() - idle_since[0] > 5:
            break

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(log, ensure_ascii=False, indent=2))
    print(f">>> 完成，{len(log)} 筆 → {output}", flush=True)


async def mode_listen(ctx: BrowserContext, output: Path) -> None:
    """持續監聽，每筆即時 append 到 JSONL"""
    output.parent.mkdir(parents=True, exist_ok=True)
    f = output.open("a")

    async def on_record(r):
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush()
        print(f"  + {r['url'].split('/')[-1]}", flush=True)

    attach_all(ctx, on_record)
    print(f">>> 監聽中，寫入 {output}（Ctrl+C 停止）", flush=True)
    try:
        await asyncio.get_event_loop().create_future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    f.close()


async def mode_watch(ctx: BrowserContext) -> None:
    """監聽並即時印到 stdout（測試用）"""
    async def on_record(r):
        print(json.dumps(r, ensure_ascii=False), flush=True)

    attach_all(ctx, on_record)
    print(">>> watch 模式（Ctrl+C 停止）", flush=True)
    try:
        await asyncio.get_event_loop().create_future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass


# ── 主程式 ────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode")

    f = sub.add_parser("fetch", help="reload extension 抓 initial sync")
    f.add_argument("--since", help="只保留此日期之後（YYYY-MM-DD）")
    f.add_argument("--output", type=Path,
                   default=Path(__file__).parent / "captured.json")

    l = sub.add_parser("listen", help="持續監聽新訊息")
    l.add_argument("--output", type=Path,
                   default=Path(__file__).parent / "captured.jsonl")

    sub.add_parser("watch", help="即時印到 stdout")

    args = p.parse_args()
    if not args.mode:
        args.mode = "fetch"
        args.since = None
        args.output = Path(__file__).parent / "captured.json"
    return args


async def main():
    args = parse_args()
    async with async_playwright() as p:
        print(f">>> 連接 CDP: {CDP_URL}", flush=True)
        b = await p.chromium.connect_over_cdp(CDP_URL)
        ctx = b.contexts[0]
        if args.mode == "fetch":
            since = None
            if args.since:
                from datetime import datetime
                since = datetime.fromisoformat(args.since).timestamp()
            await mode_fetch(ctx, args.output, since)
        elif args.mode == "listen":
            await mode_listen(ctx, args.output)
        elif args.mode == "watch":
            await mode_watch(ctx)
        try:
            await b.close()
        except Exception:
            pass


asyncio.run(main())
