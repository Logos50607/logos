# /// script
# dependencies = ["playwright"]
# ///
"""
send_api.py - 透過 LINE GW API（E2EE V2）直接發送文字訊息

原理：
  1. reload page → 取得 X-Line-Access token
  2. 從 localStorage 取得我的 mid 與 sender keyId
  3. 呼叫 getLastE2EEPublicKeys 取得對方公鑰
  4. encrypt_e2ee.encrypt_message → chunks
  5. 直接呼叫 sendMessage GW API（不觸發 UI）

用法：
  uv run send_api.py --to <mid> --text "訊息內容"
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. get_my_info(page)         - 從 localStorage 取 mid + senderKeyId
# 2. get_recipient_key(...)    - getLastE2EEPublicKeys API
# 3. send_e2ee_text(...)       - 完整發送流程
# 4. main（standalone）

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from gw_client import CDP_URL, EXT_ID, find_ext_page, get_access_token, compute_hmac, call_api
from encrypt_e2ee import encrypt_message

_PATH_SEND = "/api/talk/thrift/Talk/TalkService/sendMessage"
_PATH_KEYS = "/api/talk/thrift/Talk/TalkService/getLastE2EEPublicKeys"


# ── 1. 取得我的 mid 與 key ID ─────────────────────────────────────

async def get_my_info(page) -> tuple[str, int]:
    """從 localStorage lcs_secure_<mid> 掃出我的 mid 與最新 sender keyId。"""
    my_mid = await page.evaluate("""
        Object.keys(localStorage)
            .find(k => k.startsWith('lcs_secure_'))
            ?.replace('lcs_secure_', '')
    """)
    if not my_mid:
        raise RuntimeError("找不到 localStorage lcs_secure_* 金鑰，請先登入")

    from encrypt_e2ee import _SANDBOX_JS
    enc = await page.evaluate(f"localStorage.getItem('lcs_secure_{my_mid}')")
    r = await page.evaluate(_SANDBOX_JS,
                            {'command': 'decrypt_with_storage_key', 'payload': enc})
    if 'error' in r:
        raise RuntimeError(f"decrypt storage 失敗: {r['error']}")

    store = json.loads(r['ok'])
    key_ids = [int(k) for k in store.get('exportedKeyMap', {}).keys()]
    if not key_ids:
        raise RuntimeError("exportedKeyMap 為空，E2EE 未初始化")
    return my_mid, max(key_ids)  # 使用最新 key ID


# ── 2. 取得對方公鑰 ───────────────────────────────────────────────

async def get_recipient_key(page, token: str, recipient_mid: str) -> tuple[int, str]:
    """呼叫 getLastE2EEPublicKeys，回傳 (keyId, pubKeyB64)。"""
    body_obj = [[recipient_mid]]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, token, _PATH_KEYS, body_str)
    result = call_api(_PATH_KEYS, body_obj, token, hmac)
    if result.get('code') != 0:
        raise RuntimeError(f"getLastE2EEPublicKeys 失敗: {result}")
    key_info = result.get('data', {}).get(recipient_mid)
    if not key_info:
        raise RuntimeError(f"找不到 {recipient_mid[:20]} 的公鑰（可能未啟用 E2EE）")
    return key_info['keyId'], key_info['keyData']


# ── 3. 完整發送流程 ───────────────────────────────────────────────

async def send_e2ee_text(page, to: str, text: str) -> dict:
    """透過 GW API 發送 E2EE V2 文字訊息，不觸發 UI。"""
    print(">>> 取得 access token...", flush=True)
    token = await get_access_token(page)

    print(">>> 取得我的 mid 與 key...", flush=True)
    my_mid, sender_key_id = await get_my_info(page)
    print(f"    mid={my_mid[:20]}... keyId={sender_key_id}", flush=True)

    print(f">>> 取得 {to[:20]} 的公鑰...", flush=True)
    receiver_key_id, receiver_pub_b64 = await get_recipient_key(page, token, to)
    print(f"    keyId={receiver_key_id}", flush=True)

    seq_num = int(time.time() * 1000) & 0x7FFFFFFF
    print(f">>> E2EE 加密 (seq={seq_num})...", flush=True)
    chunks = await encrypt_message(page, to, my_mid,
                                   sender_key_id, receiver_key_id,
                                   receiver_pub_b64, seq_num, text)

    msg = {
        "from": my_mid,
        "to": to,
        "toType": 0,
        "id": f"local-{seq_num}",
        "contentType": 0,
        "contentMetadata": {"e2eeVersion": "2"},
        "hasContent": False,
        "chunks": chunks,
    }
    body_obj = [seq_num, msg]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, token, _PATH_SEND, body_str)

    print(">>> 呼叫 sendMessage API...", flush=True)
    result = call_api(_PATH_SEND, body_obj, token, hmac)
    if result.get('code') != 0:
        return {'error': f"sendMessage 失敗: {result}"}
    return {'ok': True, 'seq': seq_num}


# ── 4. 主程式 ─────────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Send LINE message via GW API (E2EE V2)")
    p.add_argument("--to",   required=True, help="目標 mid（U 開頭，1-on-1 only）")
    p.add_argument("--text", required=True, help="訊息內容")
    args = p.parse_args()

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        result = await send_e2ee_text(page, args.to, args.text)
        if result.get('ok'):
            print(f">>> 成功！seq={result['seq']}", flush=True)
        else:
            print(f">>> 失敗: {result['error']}", flush=True)
        try:
            await b.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
