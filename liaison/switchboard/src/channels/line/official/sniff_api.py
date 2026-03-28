# /// script
# dependencies = ["playwright", "qrcode[pil]", "zxing-cpp", "pillow"]
# ///
"""
sniff_api.py - 開啟帶 CDP debug port 的瀏覽器，讓使用者手動操作同時監聽 API

用法：
  uv run sniff_api.py [--qr-port 8889] [--cdp-port 9223] [--output /tmp/api-log.json]

操作：
  1. 登入後在瀏覽器裡手動建立 Provider / Channel
  2. 此 terminal 會即時印出攔截到的 POST/PUT API，並即時寫入 --output
  3. 按 Enter 結束
"""
import argparse, asyncio, json, sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
import login

_LOG: list[dict] = []
_RESP_LOG: list[dict] = []
_OUT: Path = Path("/tmp/api-log.json")


def _on_request(req):
    host = urlparse(req.url).hostname or ""
    if not any(h in host for h in ("line.biz", "line.me", "line-scdn.net")):
        return
    if req.method in ("GET", "OPTIONS", "HEAD"):
        return
    entry = {
        "method":  req.method,
        "url":     req.url,
        "headers": {k: v for k, v in req.headers.items()
                    if k.lower() in ("content-type", "authorization",
                                     "x-line-channeltoken", "cookie", "origin")},
        "body":    req.post_data,
    }
    _LOG.append(entry)
    # 即時寫入，不等 Enter
    _OUT.write_text(json.dumps(_LOG, indent=2, ensure_ascii=False))
    print(f"\n  ▶ {req.method} {req.url}")
    if req.post_data:
        print(f"    body: {req.post_data[:300]}", flush=True)


async def _on_response(resp):
    from urllib.parse import urlparse
    host = urlparse(resp.url).hostname or ""
    if not any(h in host for h in ("line.biz", "line.me")):
        return
    if resp.request.method in ("GET", "OPTIONS", "HEAD"):
        return
    try:
        body = await resp.text()
    except Exception:
        body = ""
    if not body or body == "{}":
        return
    entry = {"url": resp.url, "status": resp.status, "body": body[:1000]}
    _RESP_LOG.append(entry)
    Path(str(_OUT).replace("api-log", "api-resp-log")).write_text(
        json.dumps(_RESP_LOG, indent=2, ensure_ascii=False))
    print(f"    ← {resp.status} {body[:200]}", flush=True)


async def main(args):
    global _OUT
    _OUT = Path(args.output)
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[f"--remote-debugging-port={args.cdp_port}",
                  "--disable-blink-features=AutomationControlled",
                  "--no-sandbox"],
        )
        ctx  = await browser.new_context(storage_state=login.load_session())
        page = await ctx.new_page()

        # 監聽整個 context 的所有分頁流量（包含新開的分頁）
        ctx.on("request", _on_request)
        ctx.on("response", _on_response)

        await login.ensure_logged_in(page, args.qr_port)

        print(f"\n>>> 已登入，正在監聽 API 請求（即時寫入 {args.output}）")
        print(">>> 請在瀏覽器裡手動建立 Provider / Channel")
        print(">>> 完成後按 Enter 結束\n")

        await asyncio.get_event_loop().run_in_executor(None, input)

        print(f"\n>>> 共錄到 {len(_LOG)} 筆 API")
        await browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--qr-port",  type=int, default=8889)
    ap.add_argument("--cdp-port", type=int, default=9223)
    ap.add_argument("--output",   default="/tmp/api-log.json")
    asyncio.run(main(ap.parse_args()))
