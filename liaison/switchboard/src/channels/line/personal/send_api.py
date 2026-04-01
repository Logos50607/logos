# /// script
# dependencies = ["playwright"]
# ///
"""
send_api.py - 透過 LINE GW API（E2EE V2）直接發送文字訊息

原理：
  1. reload page → 取得 X-Line-Access token
  2. 從 localStorage 取得我的 mid 與 sender keyId
  3. 呼叫 getLastE2EEPublicKeys 取得對方最新公鑰
  4. encrypt_e2ee.encrypt_message → chunks
  5. 直接呼叫 sendMessage GW API（不觸發 UI / 已讀）
  6. code 82/84 → 重取對方公鑰重試；code 83 → fatal（需重登）

用法：
  uv run send_api.py --to <mid> --text "訊息內容"
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. get_my_info(page)            - 從 localStorage 取 mid + senderKeyId
# 2. get_recipient_key(...)       - getLastE2EEPublicKeys API
# 3. _do_send(...)                - 單次 encrypt + sendMessage（key 可注入）
# 4. send_e2ee_text(...)          - 帶重試的完整流程
# 5. main（standalone）

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from gw_client import CDP_URL, find_ext_page, get_access_token, compute_hmac, call_api
from encrypt_e2ee import (encrypt_message, _SANDBOX_JS,
                          _load_my_key, make_decrypt_channel, decrypt_e2ee_chunks)

_PATH_SEND      = "/api/talk/thrift/Talk/TalkService/sendMessage"
_PATH_NEGOTIATE = "/api/talk/thrift/Talk/TalkService/negotiateE2EEPublicKey"

# LINE E2EE server 錯誤碼
_E2EE_RETRY_ENCRYPT      = 82  # channel cache 過期 → 重取 key 重試
_E2EE_UPDATE_SENDER_KEY  = 83  # 我的 key 已失效   → fatal，需重登
_E2EE_UPDATE_RECEIVER_KEY = 84 # 對方 key 已輪換   → 重取 key 重試


# ── 1. 取得我的 mid 與 key ID ─────────────────────────────────────

async def get_my_info(page) -> tuple[str, int]:
    """從 localStorage lcs_secure_<mid> 掃出我的 mid 與最新 sender keyId。"""
    my_mid = await page.evaluate(
        "Object.keys(localStorage).find(k=>k.startsWith('lcs_secure_'))"
        "?.replace('lcs_secure_','')"
    )
    if not my_mid:
        raise RuntimeError("找不到 lcs_secure_* 金鑰，請先登入")

    enc = await page.evaluate(f"localStorage.getItem('lcs_secure_{my_mid}')")
    r = await page.evaluate(_SANDBOX_JS,
                            {'command': 'decrypt_with_storage_key', 'payload': enc})
    if 'error' in r:
        raise RuntimeError(f"decrypt storage 失敗: {r['error']}")

    store = json.loads(r['ok'])
    key_ids = [int(k) for k in store.get('exportedKeyMap', {}).keys()]
    if not key_ids:
        raise RuntimeError("exportedKeyMap 為空，E2EE 未初始化")
    return my_mid, max(key_ids)


# ── 2. 取得對方公鑰 ───────────────────────────────────────────────

async def get_recipient_key(page, token: str, recipient_mid: str) -> tuple[int, str]:
    """呼叫 negotiateE2EEPublicKey，回傳 (keyId, pubKeyB64)。"""
    body_obj = [recipient_mid]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, token, _PATH_NEGOTIATE, body_str)
    result = call_api(_PATH_NEGOTIATE, body_obj, token, hmac)
    if result.get('code') != 0:
        raise RuntimeError(f"negotiateE2EEPublicKey 失敗: {result}")
    pub_key = result.get('data', {}).get('publicKey')
    if not pub_key:
        raise RuntimeError(f"找不到 {recipient_mid[:20]} 的公鑰（可能未啟用 E2EE）")
    return pub_key['keyId'], pub_key['keyData']


# ── 3. 單次 encrypt + sendMessage（key 可注入）───────────────────

async def _do_send(page, to: str, text: str, token: str,
                   my_mid: str, sender_key_id: int,
                   receiver_key_id: int, receiver_pub_b64: str,
                   reply_to_id: str | None = None) -> dict:
    """用給定的 key 加密並呼叫 sendMessage，回傳原始 API 結果。"""
    seq_num = int(time.time() * 1000) & 0x7FFFFFFF
    chunks  = await encrypt_message(page, to, my_mid,
                                    sender_key_id, receiver_key_id,
                                    receiver_pub_b64, seq_num,
                                    json.dumps({'text': text}))
    msg = {
        "from": my_mid, "to": to, "toType": 0,
        "id": f"local-{seq_num}", "contentType": 0,
        "contentMetadata": {"e2eeVersion": "2"},
        "hasContent": False, "chunks": chunks,
    }
    if reply_to_id:
        msg["relatedMessageId"]      = reply_to_id
        msg["messageRelationType"]   = 3
        msg["relatedMessageServiceCode"] = 1
    body_obj = [seq_num, msg]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, token, _PATH_SEND, body_str)
    result = call_api(_PATH_SEND, body_obj, token, hmac)
    return result | {'_seq': seq_num}


# ── 4. 帶重試的完整流程 ───────────────────────────────────────────

async def send_e2ee_text(page, to: str, text: str,
                         reply_to_id: str | None = None) -> dict:
    """發送 E2EE V2 訊息；遇 key 過期自動重取重試（最多 2 次）。"""
    print(">>> 取得 token...", flush=True)
    token = await get_access_token(page)

    print(">>> 取得我的 key...", flush=True)
    my_mid, sender_key_id = await get_my_info(page)
    print(f"    mid={my_mid[:20]}... senderKeyId={sender_key_id}", flush=True)

    print(f">>> 取得 {to[:20]} 的公鑰...", flush=True)
    receiver_key_id, receiver_pub_b64 = await get_recipient_key(page, token, to)
    print(f"    receiverKeyId={receiver_key_id}", flush=True)

    for attempt in range(3):
        print(f">>> 加密並發送（attempt {attempt+1}）...", flush=True)
        result = await _do_send(page, to, text, token,
                                my_mid, sender_key_id,
                                receiver_key_id, receiver_pub_b64,
                                reply_to_id=reply_to_id)
        code = result.get('code', -1)
        seq  = result.get('_seq')

        if code == 0:
            return {'ok': True, 'seq': seq}

        if code == _E2EE_UPDATE_SENDER_KEY:
            return {'error': '我的 E2EE key 已失效（code 83），需重新登入'}

        if code in (_E2EE_RETRY_ENCRYPT, _E2EE_UPDATE_RECEIVER_KEY):
            print(f"    key 過期（code {code}），重取對方公鑰重試...", flush=True)
            receiver_key_id, receiver_pub_b64 = await get_recipient_key(page, token, to)
            continue

        return {'error': f"sendMessage 失敗 code={code}: {result}"}

    return {'error': '重試 3 次仍失敗'}


# ── 5. 解密收到的訊息 ─────────────────────────────────────────────

async def decrypt_e2ee_message(page, msg: dict, my_mid: str, token: str,
                                ltsm_cache: dict, chan_cache: dict,
                                pub_store: dict, debug_log=None) -> str | None:
    """
    解密單則收到的 E2EE V2 訊息，回傳明文 text 或 None。

    ltsm_cache: {r_key_id: my_ltsm_key_id}
    chan_cache:  {(my_ltsm_id, sender_mid, s_key_id): channel_ltsm_id}
    pub_store:   {key_id_str: pub_b64}  ← 扁平結構，keyId 全域唯一
    debug_log:   Path → 只有第一則訊息傳入，逐步記錄失敗原因
    """
    import base64, struct
    from datetime import datetime as _dt

    def _dlog(msg_str):
        if debug_log:
            with open(debug_log, "a") as _f:
                _f.write(f"  [{_dt.now().strftime('%H:%M:%S')}] {msg_str}\n")

    chunks = msg.get("chunks")
    if not chunks or len(chunks) < 5:
        _dlog(f"skip: chunks={type(chunks)} len={len(chunks) if chunks else 0}")
        return None
    sender_mid = msg.get("from", "")
    if not sender_mid:
        return None

    try:
        s_key_id = struct.unpack_from('>I', base64.b64decode(chunks[3])[:4])[0]
        r_key_id = struct.unpack_from('>I', base64.b64decode(chunks[4])[:4])[0]
        _dlog(f"r_key_id={r_key_id} s_key_id={s_key_id}")
    except Exception as e:
        _dlog(f"parse key_id 失敗: {e}")
        return None

    # 判斷方向：自己發出 → 私鑰=s_key_id；收到 → 私鑰=r_key_id
    i_am_sender = (sender_mid == my_mid)
    if i_am_sender:
        my_key_id    = s_key_id
        other_key_id = r_key_id
        other_mid    = msg.get("to", "")
        from_mid, to_mid = my_mid, other_mid
    else:
        my_key_id    = r_key_id
        other_key_id = s_key_id
        other_mid    = sender_mid
        from_mid, to_mid = sender_mid, msg.get("to", "")

    # 載入我的私鑰
    if my_key_id not in ltsm_cache:
        try:
            ltsm_cache[my_key_id] = await _load_my_key(page, my_mid, my_key_id)
            _dlog(f"_load_my_key OK: ltsm={ltsm_cache[my_key_id]}")
        except Exception as e:
            _dlog(f"_load_my_key 失敗 (my_key_id={my_key_id}): {e}")
            return None
    my_ltsm = ltsm_cache[my_key_id]

    # 取得對方公鑰（扁平 pub_store，找不到才打 API）
    other_key_str = str(other_key_id)
    if other_key_str not in pub_store:
        try:
            fetched_key_id, pub_b64 = await get_recipient_key(page, token, other_mid)
            pub_store[str(fetched_key_id)] = pub_b64
            _dlog(f"get_recipient_key OK: keyId={fetched_key_id}")
        except Exception as e:
            _dlog(f"get_recipient_key 失敗: {e}")
            return None
    if other_key_str not in pub_store:
        _dlog(f"other keyId={other_key_id} 不在 store，且 API 回傳的是不同 key（已輪換）")
        msg["_decrypt_skip"] = True
        return None
    other_pub = pub_store[other_key_str]

    # 建立解密 channel（cache by (my_ltsm, other_mid, other_key_id)）
    chan_key = (my_ltsm, other_mid, other_key_id)
    if chan_key not in chan_cache:
        try:
            chan_cache[chan_key] = await make_decrypt_channel(page, my_ltsm, other_pub)
            _dlog(f"make_decrypt_channel OK: channel={chan_cache[chan_key]}")
        except Exception as e:
            _dlog(f"make_decrypt_channel 失敗: {e}")
            return None
    channel_id = chan_cache[chan_key]

    try:
        plaintext = await decrypt_e2ee_chunks(
            page, chunks,
            from_mid, to_mid,
            int(msg.get("contentType", 0)),
            channel_id,
        )
    except Exception as e:
        _dlog(f"decrypt_e2ee_chunks 失敗: {e}")
        if "authentication failure" in str(e) or "Failed to decrypt" in str(e):
            msg["_decrypt_skip"] = True
        return None
    _dlog(f"decrypt_e2ee_chunks → {repr(plaintext[:40]) if plaintext else None}")
    if not plaintext:
        return None
    try:
        data = json.loads(plaintext)
        return data.get("text")
    except Exception as e:
        _dlog(f"json.loads 失敗: {e}, raw={repr(plaintext[:40])}")
        return None


# ── 6. 收回訊息 ───────────────────────────────────────────────────

_PATH_UNSEND = "/api/talk/thrift/Talk/TalkService/unsendMessage"

async def unsend_message(page, msg_id: str) -> dict:
    """收回（撤回）已發送的訊息。"""
    token = await get_access_token(page)
    body_obj = [{"messageId": msg_id}]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, token, _PATH_UNSEND, body_str)
    result = call_api(_PATH_UNSEND, body_obj, token, hmac)
    if result.get("code") == 0:
        return {"ok": True}
    return {"error": f"unsendMessage code={result.get('code')}: {result}"}


# ── 6. 主程式 ─────────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Send LINE message via GW API (E2EE V2)")
    p.add_argument("--to",   required=True, help="目標 mid（U 開頭，1-on-1 only）")
    p.add_argument("--text", required=True, help="訊息內容")
    args = p.parse_args()

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        result = await send_e2ee_text(page, args.to, args.text)
        print(f">>> {'成功 seq='+str(result['seq']) if result.get('ok') else '失敗: '+result['error']}",
              flush=True)
        try:
            await b.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
