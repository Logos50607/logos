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
                          _load_my_key, make_decrypt_channel, decrypt_e2ee_chunks,
                          unwrap_group_key)

_PATH_SEND      = "/api/talk/thrift/Talk/TalkService/sendMessage"
_PATH_NEGOTIATE = "/api/talk/thrift/Talk/TalkService/negotiateE2EEPublicKey"
_PATH_GROUP_KEY = "/api/talk/thrift/Talk/TalkService/getLastE2EEGroupSharedKey"


def _pub_data(v) -> str:
    """從 pub_store 條目取 keyData（相容新舊格式）。"""
    return v["data"] if isinstance(v, dict) else v

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
    for _attempt in range(20):
        r = await page.evaluate(_SANDBOX_JS,
                                {'command': 'decrypt_with_storage_key', 'payload': enc})
        if 'ok' in r:
            break
        err = str(r.get('error', ''))
        if 'ltsm_not_ready' not in err and 'no iframe' not in err:
            raise RuntimeError(f"decrypt storage 失敗: {r['error']}")
        await asyncio.sleep(1)
    else:
        raise RuntimeError("LTSM sandbox 20 秒內未就緒")

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


async def load_group_key(page, token: str, chat_mid: str,
                         my_personal_ltsm: int, pub_store: dict) -> int:
    """
    取得並解包群組私鑰，回傳群組私鑰的 LTSM slot ID。

    流程：
      1. getLastE2EEGroupSharedKey → {groupKeyId, creatorKeyId, encryptedSharedKey}
      2. 從 pub_store 取 creator 公鑰（需是 creatorKeyId 對應的 key）
      3. make_decrypt_channel(my_personal_ltsm, creator_pub) → channel_id
      4. unwrap_group_key(channel_id, encryptedSharedKey) → group_ltsm_id
    """
    body_obj = [1, chat_mid]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, token, _PATH_GROUP_KEY, body_str)
    result = call_api(_PATH_GROUP_KEY, body_obj, token, hmac)
    if result.get('code') != 0:
        raise RuntimeError(f"getLastE2EEGroupSharedKey 失敗: {result}")
    d = result.get('data', {})
    creator_key_id = d.get('creatorKeyId')
    enc_shared_key = d.get('encryptedSharedKey', '')
    if not enc_shared_key:
        raise RuntimeError(f"群組 {chat_mid[:16]} 無 encryptedSharedKey")

    # 取 creator 公鑰（通常已在 pub_store，否則打 API）
    creator_key_str = str(creator_key_id)
    if creator_key_str not in pub_store:
        creator_mid = d.get('creator', '')
        fetched_id, pub_b64 = await get_recipient_key(page, token, creator_mid)
        pub_store[str(fetched_id)] = {"data": pub_b64, "createdTime": int(time.time() * 1000)}
    creator_pub = _pub_data(pub_store[creator_key_str])

    # 建立 channel：我的個人私鑰 + creator 公鑰 → ECDH shared secret
    channel_id = await make_decrypt_channel(page, my_personal_ltsm, creator_pub)
    # 解包群組私鑰
    group_ltsm_id = await unwrap_group_key(page, channel_id, enc_shared_key)
    return group_ltsm_id


# ── 3. 單次 encrypt + sendMessage（key 可注入）───────────────────

async def _do_send(page, to: str, text: str, token: str,
                   my_mid: str, sender_key_id: int,
                   receiver_key_id: int, receiver_pub_b64: str,
                   reply_to_id: str | None = None,
                   to_type: int = 0) -> dict:
    """用給定的 key 加密並呼叫 sendMessage，回傳原始 API 結果。"""
    seq_num = int(time.time() * 1000) & 0x7FFFFFFF
    chunks  = await encrypt_message(page, to, my_mid,
                                    sender_key_id, receiver_key_id,
                                    receiver_pub_b64, seq_num,
                                    json.dumps({'text': text}))
    msg = {
        "from": my_mid, "to": to, "toType": to_type,
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

def _group_members_from_history(group_mid: str, my_mid: str) -> list[str]:
    """從訊息歷史推導群組成員（曾發言者，不含自己）。"""
    import json
    from pathlib import Path
    msgs_file = Path(__file__).parent / "data" / "messages.json"
    data = json.loads(msgs_file.read_text())
    msgs = data.get(group_mid, [])
    return list({m.get("from") for m in msgs if m.get("from")} - {my_mid, None})


async def send_e2ee_group_text(page, group_mid: str, text: str,
                                reply_to_id: str | None = None,
                                _token: str | None = None,
                                _my_mid: str | None = None,
                                _sender_key_id: int | None = None) -> dict:
    """對群組每個成員各加密一份並發送；回傳 {ok, seq} 或 {error}。"""
    token = _token or await get_access_token(page)
    my_mid = _my_mid
    sender_key_id = _sender_key_id
    if my_mid is None or sender_key_id is None:
        my_mid, sender_key_id = await get_my_info(page)
    members = _group_members_from_history(group_mid, my_mid)
    if not members:
        return {"error": "找不到群組成員（訊息歷史為空）"}

    last_seq = None
    for member_mid in members:
        print(f">>> 取得 {member_mid[:20]} 的公鑰...", flush=True)
        try:
            r_key_id, r_pub = await get_recipient_key(page, token, member_mid)
        except Exception as e:
            print(f"    公鑰失敗: {e}", flush=True)
            continue
        for attempt in range(3):
            result = await _do_send(page, group_mid, text, token,
                                    my_mid, sender_key_id, r_key_id, r_pub,
                                    reply_to_id=reply_to_id, to_type=2)
            code = result.get("code", -1)
            last_seq = result.get("_seq")
            if code == 0:
                break
            if code in (_E2EE_RETRY_ENCRYPT, _E2EE_UPDATE_RECEIVER_KEY):
                r_key_id, r_pub = await get_recipient_key(page, token, member_mid)
                continue
            return {"error": f"sendMessage 失敗 code={code} body={result.get('_body','')[:300]}"}
        else:
            return {"error": "重試 3 次仍失敗"}

    return {"ok": True, "seq": last_seq}


async def send_e2ee_text(page, to: str, text: str,
                         reply_to_id: str | None = None,
                         _token: str | None = None,
                         _my_mid: str | None = None,
                         _sender_key_id: int | None = None) -> dict:
    """發送 E2EE V2 訊息；群組自動分派給每個成員。"""
    if not to.startswith("U"):
        return await send_e2ee_group_text(page, to, text, reply_to_id,
                                          _token=_token, _my_mid=_my_mid,
                                          _sender_key_id=_sender_key_id)
    print(">>> 取得 token...", flush=True)
    token = _token or await get_access_token(page)

    print(">>> 取得我的 key...", flush=True)
    my_mid = _my_mid
    sender_key_id = _sender_key_id
    if my_mid is None or sender_key_id is None:
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
                                pub_store: dict, debug_log=None,
                                my_personal_key_id: int | None = None) -> str | None:
    """
    解密單則 E2EE V2 訊息，回傳明文 text 或 None。

    ltsm_cache:         {key_id: ltsm_slot_id}  ← 含個人金鑰與群組金鑰
    chan_cache:          {(my_ltsm_id, other_mid, other_key_id): channel_ltsm_id}
    pub_store:           {key_id_str: {data, createdTime}}
    my_personal_key_id:  我的個人 E2EE key id（用於解包群組金鑰）
    debug_log:           Path → 只對第一則記錄步驟
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

    # 判斷方向與金鑰：群組訊息固定用 r_key_id（群組金鑰），1-to-1 依發送方向
    chat_mid = msg.get("to", "")
    is_group = chat_mid.startswith("C") or chat_mid.startswith("R")
    if is_group:
        # 群組 E2EE：r_key_id = 群組共享金鑰 ID（所有訊息相同）
        #            s_key_id = 發送者個人金鑰（用於建立 channel）
        my_key_id    = r_key_id
        other_key_id = s_key_id
        other_mid    = sender_mid
        from_mid, to_mid = sender_mid, chat_mid
        _dlog(f"群組訊息: group_key={my_key_id} sender_key={other_key_id}")
    elif sender_mid == my_mid:
        # 1-to-1 自己發出：私鑰 = s_key_id（我的個人金鑰）
        my_key_id    = s_key_id
        other_key_id = r_key_id
        other_mid    = chat_mid
        from_mid, to_mid = my_mid, chat_mid
    else:
        # 1-to-1 收到：私鑰 = r_key_id（我的個人金鑰）
        my_key_id    = r_key_id
        other_key_id = s_key_id
        other_mid    = sender_mid
        from_mid, to_mid = sender_mid, chat_mid

    # 載入我的私鑰（群組金鑰需透過 load_group_key；個人金鑰掃 LTSM）
    if my_key_id not in ltsm_cache:
        if is_group:
            # 群組金鑰：需先確保個人金鑰已載入，再解包群組金鑰
            personal_key_id = my_personal_key_id
            if personal_key_id is None or personal_key_id not in ltsm_cache:
                _dlog(f"群組金鑰解包失敗：個人金鑰 {personal_key_id} 未在 ltsm_cache")
                return None
            personal_ltsm = ltsm_cache[personal_key_id]
            if personal_ltsm == -1:
                return None
            try:
                ltsm_cache[my_key_id] = await load_group_key(
                    page, token, chat_mid, personal_ltsm, pub_store)
                _dlog(f"load_group_key OK: group_key={my_key_id} ltsm={ltsm_cache[my_key_id]}")
            except Exception as e:
                _dlog(f"load_group_key 失敗: {e}")
                ltsm_cache[my_key_id] = -1
                return None
        else:
            try:
                ltsm_cache[my_key_id] = await _load_my_key(page, my_mid, my_key_id)
                _dlog(f"_load_my_key OK: ltsm={ltsm_cache[my_key_id]}")
            except Exception as e:
                _dlog(f"_load_my_key 失敗 (my_key_id={my_key_id}): {e}")
                ltsm_cache[my_key_id] = -1
                return None
    if ltsm_cache[my_key_id] == -1:
        return None
    my_ltsm = ltsm_cache[my_key_id]

    # 取得對方公鑰（扁平 pub_store，找不到才打 API）
    other_key_str = str(other_key_id)
    if other_key_str not in pub_store:
        try:
            fetched_key_id, pub_b64 = await get_recipient_key(page, token, other_mid)
            pub_store[str(fetched_key_id)] = {"data": pub_b64, "createdTime": int(time.time() * 1000)}
            _dlog(f"get_recipient_key OK: keyId={fetched_key_id}")
        except Exception as e:
            _dlog(f"get_recipient_key 失敗: {e}")
            return None
    if other_key_str not in pub_store:
        _dlog(f"other keyId={other_key_id} 不在 store，且 API 回傳的是不同 key（已輪換）")
        msg["_decrypt_skip"] = True
        return None
    other_pub = _pub_data(pub_store[other_key_str])

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

async def unsend_message(page, msg_id: str, _token: str | None = None) -> dict:
    """收回（撤回）已發送的訊息。"""
    token = _token or await get_access_token(page)
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
