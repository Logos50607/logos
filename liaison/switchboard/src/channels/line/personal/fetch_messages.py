# /// script
# dependencies = ["playwright"]
# ///
"""
fetch_messages.py - 從 LINE GW 直接抓取所有聊天室的完整訊息

原理：
  1. 連接 CDP → 取得 X-Line-Access token
  2. 透過 ltsmSandbox iframe postMessage 計算 HMAC（不需要 Chrome open）
  3. 用 Python 直接呼叫 LINE GW API（getRecentMessagesV2）

用法：
  uv run fetch_messages.py                         # 抓所有聊天室（預設 50 則/室）
  uv run fetch_messages.py --count 200             # 每室 200 則
  uv run fetch_messages.py --chat C4abc... --count 100
  uv run fetch_messages.py --output /tmp/msgs.json
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. parse_args
# 2. get_access_token(page)      - CDP + page.on('request')
# 3. compute_hmac(page, ...)     - ltsmSandbox postMessage
# 4. call_api(path, body, token, hmac)  - Python urllib
# 5. fetch_chat_messages(...)    - getRecentMessagesV2 loop
# 6. main

import argparse
import asyncio
import json
import os
import urllib.error
import urllib.request
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
GW_BASE = "https://line-chrome-gw.line-apps.com"


# ── 1. 參數 ───────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Fetch LINE messages via GW API")
    p.add_argument("--count",  type=int, default=50,   help="每個聊天室抓幾則（預設 50）")
    p.add_argument("--chat",   default=None,            help="指定單一聊天室 mid")
    p.add_argument("--output", type=Path,
                   default=Path(__file__).parent / "messages.json",
                   help="輸出路徑")
    return p.parse_args()


# ── 2. 取得 access token ──────────────────────────────────────────

async def get_access_token(page) -> str:
    token = {}

    async def on_req(req):
        if 'line-chrome-gw' in req.url and 'x-line-access' in req.headers:
            token['v'] = req.headers['x-line-access']

    page.on('request', on_req)
    await page.reload()

    for _ in range(30):
        if 'v' in token:
            break
        await asyncio.sleep(0.5)

    if 'v' not in token:
        raise RuntimeError("無法取得 X-Line-Access token，請確認已登入")
    return token['v']


# ── 3. 計算 HMAC ──────────────────────────────────────────────────

async def compute_hmac(page, access_token: str, path: str, body: str) -> str:
    """透過 ltsmSandbox iframe 計算 X-Hmac"""
    result = await page.evaluate('''([token, path, body]) => new Promise((resolve) => {
        const iframe = document.querySelector("iframe[src*='ltsmSandbox']");
        if (!iframe) return resolve({error: "no iframe"});
        const sandboxId = new URL(iframe.src).searchParams.get("sandboxId");
        const handler = (evt) => {
            const d = evt.data;
            if (d && d.sandboxId === sandboxId && (d.type === "response" || d.type === "error")) {
                window.removeEventListener("message", handler);
                resolve(d.type === "response" ? {hmac: d.data} : {error: d.data});
            }
        };
        window.addEventListener("message", handler);
        iframe.contentWindow.postMessage({
            sandboxId,
            type: "request",
            data: {command: "get_hmac", payload: {accessToken: token, path, body}}
        }, "*");
        setTimeout(() => resolve({error: "timeout"}), 5000);
    })''', [access_token, path, body])

    if 'error' in result:
        raise RuntimeError(f"HMAC 計算失敗: {result['error']}")
    return result['hmac']


# ── 4. 呼叫 API ───────────────────────────────────────────────────

def call_api(path: str, body_obj, access_token: str, hmac: str) -> dict:
    body = json.dumps(body_obj).encode()
    req = urllib.request.Request(
        GW_BASE + path,
        data=body,
        headers={
            'content-type': 'application/json',
            'x-line-chrome-version': '3.7.2',
            'x-line-access': access_token,
            'x-hmac': hmac,
            'x-lal': 'en_US',
            'origin': f'chrome-extension://{EXT_ID}',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {'_error': e.code, '_body': e.read().decode()[:200]}


# ── 5. 抓單一聊天室訊息（含 pagination）────────────────────────────

async def _get_recent(page, access_token, chat_mid, count) -> list:
    path = "/api/talk/thrift/Talk/TalkService/getRecentMessagesV2"
    body_obj = [chat_mid, count]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, access_token, path, body_str)
    result = call_api(path, body_obj, access_token, hmac)
    if result.get('code') != 0:
        return []
    return result.get('data', [])


async def _get_previous(page, access_token, chat_mid, oldest_msg, count) -> list:
    """oldest_msg = {"id": ..., "deliveredTime": ..., "createdTime": ...}"""
    path = "/api/talk/thrift/Talk/TalkService/getPreviousMessagesV2WithRequest"
    body_obj = [{
        "messageBoxId": chat_mid,
        "endMessageId": {
            "messageId": oldest_msg["id"],
            "deliveredTime": oldest_msg.get("deliveredTime") or oldest_msg.get("createdTime"),
        },
        "messagesCount": count,
    }]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, access_token, path, body_str)
    result = call_api(path, body_obj, access_token, hmac)
    if result.get('code') != 0:
        return []
    return result.get('data', [])


async def fetch_chat_messages(page, access_token: str, chat_mid: str, count: int) -> list:
    """先抓最近 count 則，不夠再往前 paginate"""
    msgs = await _get_recent(page, access_token, chat_mid, count)
    if not msgs:
        return []

    # 若還需要更多，往前翻頁（最多再拉 3 頁避免過慢）
    all_msgs = list(msgs)
    page_size = min(count, 50)
    for _ in range(3):
        if len(msgs) < page_size:
            break  # 已到最舊
        oldest = min(msgs, key=lambda m: int(m.get("createdTime", 0)))
        prev = await _get_previous(page, access_token, chat_mid, oldest, page_size)
        prev = [m for m in prev if m["id"] != oldest["id"]]
        if not prev:
            break
        all_msgs = prev + all_msgs
        msgs = prev

    return all_msgs


# ── 6. 主程式 ─────────────────────────────────────────────────────

async def main():
    args = parse_args()

    async with async_playwright() as p:
        print(f">>> 連接 CDP: {CDP_URL}", flush=True)
        b = await p.chromium.connect_over_cdp(CDP_URL)
        ctx = b.contexts[0]
        page = next((pg for pg in ctx.pages if EXT_ID in pg.url), None)
        if not page:
            raise RuntimeError("找不到 LINE extension page，請先執行 run.py 登入")

        print(">>> 取得 access token...", flush=True)
        access_token = await get_access_token(page)

        # 取得聊天室清單（從 captured.json，若無則只抓 --chat 指定的）
        if args.chat:
            chat_mids = [args.chat]
        else:
            captured_path = Path(__file__).parent / "captured.json"
            if not captured_path.exists():
                raise RuntimeError(
                    "找不到 captured.json，請先執行 `uv run capture.py fetch`"
                )
            data = json.loads(captured_path.read_text())
            # 使用 getMessageBoxes 的 id（非 getChats 的 chatMid）
            chat_mids = []
            for r in data:
                if 'getMessageBoxes' in r['url'] and r.get('body', {}).get('code') == 0:
                    boxes = r['body'].get('data', {}).get('messageBoxes', [])
                    chat_mids.extend(b['id'] for b in boxes if 'id' in b)
            chat_mids = list(dict.fromkeys(chat_mids))  # 去重
            print(f">>> 共 {len(chat_mids)} 個聊天室", flush=True)

        results = {}
        for i, mid in enumerate(chat_mids, 1):
            print(f"  [{i}/{len(chat_mids)}] {mid[:20]}...", flush=True)
            msgs = await fetch_chat_messages(page, access_token, mid, args.count)
            results[mid] = msgs

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        total = sum(len(v) for v in results.values())
        print(f">>> 完成，{total} 則訊息 → {args.output}", flush=True)

        try:
            await b.close()
        except Exception:
            pass


asyncio.run(main())
