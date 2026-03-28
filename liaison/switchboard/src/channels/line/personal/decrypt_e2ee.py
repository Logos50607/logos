# /// script
# dependencies = ["playwright"]
# ///
"""
decrypt_e2ee.py - LINE E2EE V2 解密（透過 ltsmSandbox，無需 UI）

流程：
  1. 從 chunks 解析 IV、ciphertext、seqKeyId、senderKeyId、receiverKeyId
  2. 呼叫 getE2EEPublicKey 取得傳送方公鑰
  3. e2eekey_load_key(receiverKeyId) → keyLtsmId（我的私鑰）
  4. e2eekey_create_channel(keyLtsmId, senderPubKeyBytes) → channelLtsmId
  5. e2eechannel_decrypt_v2(channelLtsmId, ...) → plaintext bytes

公開函式：
  decrypt_chunks(page, token, message) -> dict
    回傳解密後的 JSON（文字訊息: {"text":"..."}, 圖片: {"keyMaterial":"..."}）
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. 常數
# 2. _parse_chunks(message)       - 解析 chunks base64 → bytes
# 3. _get_sender_key(...)         - getE2EEPublicKey API
# 4. _DECRYPT_V2_JS               - postMessage 解密腳本
# 5. _decrypt_v2(page, ...)       - 呼叫 sandbox 解密
# 6. decrypt_chunks(page, token, message) - 公開入口

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gw_client import compute_hmac, call_api
from encrypt_e2ee import _SANDBOX_JS, _LOAD_KEY_JS, _CREATE_CHANNEL_JS

_PATH_GET_PUBKEY = "/api/talk/thrift/Talk/TalkService/getE2EEPublicKey"


# ── 2. 解析 chunks ────────────────────────────────────────────────

def _parse_chunks(message: dict) -> tuple[bytes, int, int]:
    """
    解析訊息 chunks，回傳 (raw_ciphertext, senderKeyId, receiverKeyId)。
    raw_ciphertext = IV(16) + seqKeyId(12) + ciphertext(N)
    """
    c = message['chunks']
    iv          = base64.b64decode(c[0])   # 16 bytes
    ciphertext  = base64.b64decode(c[1])   # N bytes
    seq_key_id  = base64.b64decode(c[2])   # 12 bytes
    sender_key_id   = int.from_bytes(base64.b64decode(c[3]), 'big')
    receiver_key_id = int.from_bytes(base64.b64decode(c[4]), 'big')
    raw = iv + seq_key_id + ciphertext
    return raw, sender_key_id, receiver_key_id


# ── 3. 取得傳送方公鑰 ─────────────────────────────────────────────

async def _get_sender_key(page, token: str, sender_mid: str,
                          key_id: int) -> tuple[int, str]:
    """呼叫 getE2EEPublicKey，回傳 (keyId, pubKeyB64)。"""
    body_obj = [sender_mid, 1, key_id]  # [mid, version=1, keyId]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, token, _PATH_GET_PUBKEY, body_str)
    result = call_api(_PATH_GET_PUBKEY, body_obj, token, hmac)
    if result.get('code') != 0:
        raise RuntimeError(f"getE2EEPublicKey 失敗: {result}")
    data = result.get('data', {})
    if not data.get('keyData'):
        raise RuntimeError(f"找不到 {sender_mid[:20]} keyId={key_id} 的公鑰")
    return data['keyId'], data['keyData']


# ── 4. 解密 JS ───────────────────────────────────────────────────

_DECRYPT_V2_JS = """([chId, to, frm, sKId, rKId, ctType, rawB64]) => new Promise((resolve) => {
    const iframe = document.querySelector("iframe[src*='ltsmSandbox']");
    if (!iframe) { resolve({error: "no iframe"}); return; }
    const sandboxId = new URL(iframe.src).searchParams.get("sandboxId");
    const ciphertext = Uint8Array.from(atob(rawB64), c => c.charCodeAt(0));
    const RR = b => btoa(String.fromCharCode.apply(null, Array.from(b)));
    const handler = (evt) => {
        const d = evt.data;
        if (d && d.sandboxId === sandboxId &&
            (d.type === "response" || d.type === "error")) {
            // e2eechannel_decrypt_v2 回傳 ArrayBuffer，過濾非 ArrayBuffer 回應（stale messages）
            if (d.type === "response" && !(d.data instanceof ArrayBuffer)) return;
            window.removeEventListener("message", handler);
            if (d.type === "error") { resolve({error: String(d.data)}); return; }
            resolve({ok: RR(new Uint8Array(d.data))});
        }
    };
    window.addEventListener("message", handler);
    iframe.contentWindow.postMessage({sandboxId, type: "request",
        data: {command: "e2eechannel_decrypt_v2", ltsmKeyId: chId,
               payload: {to, from: frm, senderKeyId: sKId, receiverKeyId: rKId,
                         contentType: ctType, ciphertext}}}, "*");
    setTimeout(() => resolve({error: "timeout"}), 8000);
})"""


# ── 5. 呼叫 sandbox 解密 ─────────────────────────────────────────

async def _decrypt_v2(page, channel_ltsm_id: int,
                      to: str, frm: str,
                      sender_key_id: int, receiver_key_id: int,
                      content_type: int, raw: bytes) -> bytes:
    """呼叫 e2eechannel_decrypt_v2，回傳明文 bytes。"""
    raw_b64 = base64.b64encode(raw).decode()
    r = await page.evaluate(_DECRYPT_V2_JS,
                            [channel_ltsm_id, to, frm,
                             sender_key_id, receiver_key_id,
                             content_type, raw_b64])
    if 'error' in r:
        raise RuntimeError(f"e2eechannel_decrypt_v2 失敗: {r['error']}")
    return base64.b64decode(r['ok'])


# ── 6. 公開入口 ───────────────────────────────────────────────────

async def _get_my_mid(page) -> str:
    """從 localStorage lcs_secure_* 掃出我的 mid。"""
    my_mid = await page.evaluate(
        "Object.keys(localStorage).find(k=>k.startsWith('lcs_secure_'))"
        "?.replace('lcs_secure_','')"
    )
    if not my_mid:
        raise RuntimeError("找不到 lcs_secure_* 金鑰，請先登入")
    return my_mid


async def decrypt_chunks(page, token: str, message: dict) -> dict:
    """
    解密 E2EE V2 訊息 chunks，回傳明文 dict。

    自動判斷我是傳送方還是接收方：
    - 接收：chunks[4] 為我的 keyId，chunks[3] 為對方 keyId
    - 傳送：chunks[3] 為我的 keyId，chunks[4] 為對方 keyId

    Args:
        page    - Playwright page（LINE extension）
        token   - X-Line-Access token
        message - 含 chunks、from、to、contentType 的訊息 dict

    Returns:
        文字訊息: {"text": "..."}
        圖片訊息: {"keyMaterial": "<base64>"}
    """
    raw, sender_key_id, receiver_key_id = _parse_chunks(message)
    content_type = message.get('contentType', 0)
    my_mid = await _get_my_mid(page)

    # 判斷角色：我是傳送方或接收方
    if message['from'] == my_mid:
        # 我是傳送方：chunks[3]=我的key, chunks[4]=對方key
        my_key_id    = sender_key_id
        other_mid    = message['to']
        other_key_id = receiver_key_id
    else:
        # 我是接收方：chunks[4]=我的key, chunks[3]=對方key
        my_key_id    = receiver_key_id
        other_mid    = message['from']
        other_key_id = sender_key_id

    # 取得對方公鑰
    _, other_pub_b64 = await _get_sender_key(page, token, other_mid, other_key_id)

    # 載入我的私鑰
    enc = await page.evaluate(
        f"localStorage.getItem('lcs_secure_{my_mid}')"
    )
    r = await page.evaluate(_SANDBOX_JS,
                            {'command': 'decrypt_with_storage_key', 'payload': enc})
    if 'error' in r:
        raise RuntimeError(f"decrypt storage 失敗: {r['error']}")

    if isinstance(r['ok'], int):
        # sandbox 直接回傳 ltsmKeyId
        key_ltsm_id = r['ok']
    else:
        store = json.loads(r['ok'])
        key_b64 = store.get('exportedKeyMap', {}).get(str(my_key_id))
        if not key_b64:
            raise RuntimeError(f"exportedKeyMap 找不到 keyId {my_key_id}")
        r = await page.evaluate(_LOAD_KEY_JS, [key_b64])
        if 'error' in r:
            raise RuntimeError(f"e2eekey_load_key 失敗: {r['error']}")
        key_ltsm_id = r['ok']

    # 建立 channel（我的私鑰 × 對方公鑰）
    r = await page.evaluate(_CREATE_CHANNEL_JS, [key_ltsm_id, other_pub_b64])
    if 'error' in r:
        raise RuntimeError(f"e2eekey_create_channel 失敗: {r['error']}")
    channel_ltsm_id = r['ok']

    # 解密（to/from 使用訊息原始值，senderKeyId/receiverKeyId 同）
    plaintext = await _decrypt_v2(page, channel_ltsm_id,
                                   message['to'], message['from'],
                                   sender_key_id, receiver_key_id,
                                   content_type, raw)

    return json.loads(plaintext.decode('utf-8'))
