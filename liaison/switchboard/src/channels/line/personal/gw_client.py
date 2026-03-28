"""
gw_client.py - LINE GW API 共用工具

提供：EXT_ID / CDP_URL / GW_BASE 常數、
     find_ext_page / get_access_token / compute_hmac / call_api
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. 常數
# 2. find_ext_page(ctx)
# 3. get_access_token(page)
# 4. compute_hmac(page, token, path, body_str)
# 5. call_api(path, body_obj, token, hmac)

import asyncio
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

_EXT_ID_FILE    = Path(__file__).parent / ".ext-id"
_EXT_ID_DEFAULT = "ophjlpahpchlmihnnnihgmmeilfjmjjc"

def _load_ext_id():
    if val := os.getenv("LINE_PERSONAL_EXT_ID"): return val
    if _EXT_ID_FILE.exists(): return _EXT_ID_FILE.read_text().strip()
    return _EXT_ID_DEFAULT

EXT_ID  = _load_ext_id()
CDP_URL = os.getenv("LINE_PERSONAL_CDP_URL", "http://localhost:9222")
GW_BASE = "https://line-chrome-gw.line-apps.com"


# ── 2. find_ext_page ─────────────────────────────────────────────

def find_ext_page(ctx):
    """從 browser context 找到 LINE extension page。"""
    page = next((p for p in ctx.pages if EXT_ID in p.url), None)
    if not page:
        raise RuntimeError("找不到 LINE extension page，請先執行 run.py 登入")
    return page


# ── 3. get_access_token ──────────────────────────────────────────

async def get_access_token(page) -> str:
    """reload extension page，攔截 GW request 取得 X-Line-Access token。"""
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

    page.remove_listener('request', on_req)
    if 'v' not in token:
        raise RuntimeError("無法取得 X-Line-Access token，請確認已登入")
    return token['v']


# ── 4. compute_hmac ──────────────────────────────────────────────

async def compute_hmac(page, access_token: str, path: str, body: str) -> str:
    """透過 ltsmSandbox iframe 計算 X-Hmac。"""
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


# ── 5. call_api ──────────────────────────────────────────────────

def call_api(path: str, body_obj, access_token: str, hmac: str) -> dict:
    """直接以 Python urllib 呼叫 LINE GW API。"""
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
