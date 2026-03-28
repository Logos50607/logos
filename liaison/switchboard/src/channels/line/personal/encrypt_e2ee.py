# /// script
# dependencies = ["playwright"]
# ///
"""
encrypt_e2ee.py - LINE E2EE V2 加密（透過 ltsmSandbox postMessage，無需 UI）

流程：
  1. decrypt_with_storage_key → 取得匯出私鑰（base64）
  2. e2eekey_load_key(Uint8Array) → keyLtsmId
  3. e2eekey_create_channel(keyLtsmId, recipientPubKeyBytes) → channelLtsmId
  4. e2eechannel_encrypt_v2(channelLtsmId, ...) → raw bytes → vL chunks

公開函式：
  encrypt_message(page, to, from_mid, sender_key_id, receiver_key_id,
                  receiver_pub_key_b64, seq_num, text) -> list[str]
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. _sandbox(page, data)       - postMessage 單次 request/response
# 2. _load_my_key(page, mid, key_id) - 解密 localStorage → 載入 wasm
# 3. encrypt_message(...)       - 公開入口

import asyncio
import json

_SANDBOX_JS = """(data) => new Promise((resolve) => {
    const iframe = document.querySelector("iframe[src*='ltsmSandbox']");
    if (!iframe) { resolve({error: "no iframe"}); return; }
    const sandboxId = new URL(iframe.src).searchParams.get("sandboxId");
    const handler = (evt) => {
        const d = evt.data;
        if (d && d.sandboxId === sandboxId &&
            (d.type === "response" || d.type === "error")) {
            window.removeEventListener("message", handler);
            resolve(d.type === "response" ? {ok: d.data} : {error: String(d.data)});
        }
    };
    window.addEventListener("message", handler);
    iframe.contentWindow.postMessage({sandboxId, type: "request", data}, "*");
    setTimeout(() => resolve({error: "timeout"}), 8000);
})"""

_LOAD_KEY_JS = """([kb64]) => new Promise((resolve) => {
    const iframe = document.querySelector("iframe[src*='ltsmSandbox']");
    if (!iframe) { resolve({error: "no iframe"}); return; }
    const sandboxId = new URL(iframe.src).searchParams.get("sandboxId");
    const payload = Uint8Array.from(atob(kb64), c => c.charCodeAt(0));
    const handler = (evt) => {
        const d = evt.data;
        if (d && d.sandboxId === sandboxId &&
            (d.type === "response" || d.type === "error")) {
            window.removeEventListener("message", handler);
            resolve(d.type === "response" ? {ok: d.data} : {error: String(d.data)});
        }
    };
    window.addEventListener("message", handler);
    iframe.contentWindow.postMessage({sandboxId, type: "request",
        data: {command: "e2eekey_load_key", payload}}, "*");
    setTimeout(() => resolve({error: "timeout"}), 8000);
})"""

_CREATE_CHANNEL_JS = """([keyId, pubB64]) => new Promise((resolve) => {
    const iframe = document.querySelector("iframe[src*='ltsmSandbox']");
    if (!iframe) { resolve({error: "no iframe"}); return; }
    const sandboxId = new URL(iframe.src).searchParams.get("sandboxId");
    const payload = Uint8Array.from(atob(pubB64), c => c.charCodeAt(0));
    const handler = (evt) => {
        const d = evt.data;
        if (d && d.sandboxId === sandboxId &&
            (d.type === "response" || d.type === "error")) {
            window.removeEventListener("message", handler);
            resolve(d.type === "response" ? {ok: d.data} : {error: String(d.data)});
        }
    };
    window.addEventListener("message", handler);
    iframe.contentWindow.postMessage({sandboxId, type: "request",
        data: {command: "e2eekey_create_channel", ltsmKeyId: keyId, payload}}, "*");
    setTimeout(() => resolve({error: "timeout"}), 8000);
})"""

_ENCRYPT_V2_JS = """([chId, to, frm, sKId, rKId, seqN, pt]) => new Promise((resolve) => {
    const iframe = document.querySelector("iframe[src*='ltsmSandbox']");
    if (!iframe) { resolve({error: "no iframe"}); return; }
    const sandboxId = new URL(iframe.src).searchParams.get("sandboxId");
    const ptBytes = new TextEncoder().encode(pt);
    const LR = (n, len) => {
        const b = new Uint8Array(len);
        for (let i = len-1; i >= 0; i--) { b[i] = n & 0xff; n = Math.floor(n / 256); }
        return b;
    };
    const RR = b => btoa(String.fromCharCode.apply(null, Array.from(b)));
    const handler = (evt) => {
        const d = evt.data;
        if (d && d.sandboxId === sandboxId &&
            (d.type === "response" || d.type === "error")) {
            window.removeEventListener("message", handler);
            if (d.type === "error") { resolve({error: String(d.data)}); return; }
            const e = new Uint8Array(d.data);
            // vL: [IV(0:16), ciphertext(28:), seqKeyId(16:28), senderKeyId, receiverKeyId]
            resolve({ok: [RR(e.slice(0,16)), RR(e.slice(28)), RR(e.slice(16,28)),
                          RR(LR(sKId,4)), RR(LR(rKId,4))]});
        }
    };
    window.addEventListener("message", handler);
    iframe.contentWindow.postMessage({sandboxId, type: "request",
        data: {command: "e2eechannel_encrypt_v2", ltsmKeyId: chId,
               payload: {to, from: frm, senderKeyId: sKId, receiverKeyId: rKId,
                         contentType: 0, sequenceNumber: BigInt(seqN), plaintext: ptBytes}}}, "*");
    setTimeout(() => resolve({error: "timeout"}), 8000);
})"""


# ── 1. 載入私鑰 ───────────────────────────────────────────────────

async def _load_my_key(page, my_mid: str, sender_key_id: int) -> int:
    """解密 localStorage，取出私鑰，載入 wasm。回傳 keyLtsmId（整數）。"""
    enc = await page.evaluate(f"localStorage.getItem('lcs_secure_{my_mid}')")
    if not enc:
        raise RuntimeError(f"localStorage 找不到 lcs_secure_{my_mid}")

    r = await page.evaluate(_SANDBOX_JS, {'command': 'decrypt_with_storage_key', 'payload': enc})
    if 'error' in r:
        raise RuntimeError(f"decrypt_with_storage_key 失敗: {r['error']}")

    store = json.loads(r['ok'])
    key_b64 = store.get('exportedKeyMap', {}).get(str(sender_key_id))
    if not key_b64:
        raise RuntimeError(f"exportedKeyMap 找不到 keyId {sender_key_id}")

    r = await page.evaluate(_LOAD_KEY_JS, [key_b64])
    if 'error' in r:
        raise RuntimeError(f"e2eekey_load_key 失敗: {r['error']}")
    return r['ok']


# ── 2. 公開入口 ───────────────────────────────────────────────────

async def encrypt_message(page,
                          to: str, from_mid: str,
                          sender_key_id: int, receiver_key_id: int,
                          receiver_pub_key_b64: str,
                          seq_num: int, text: str) -> list:
    """
    E2EE V2 加密文字訊息，回傳 5 個 base64 chunks。

    Args:
        page               - Playwright page（LINE extension）
        to                 - 收件人 mid
        from_mid           - 我的 mid
        sender_key_id      - 我的 E2EE key id（int）
        receiver_key_id    - 對方 E2EE key id（int）
        receiver_pub_key_b64 - 對方 Curve25519 公鑰（base64）
        seq_num            - 訊息 sequence number
        text               - 純文字內容
    """
    key_ltsm_id = await _load_my_key(page, from_mid, sender_key_id)

    r = await page.evaluate(_CREATE_CHANNEL_JS, [key_ltsm_id, receiver_pub_key_b64])
    if 'error' in r:
        raise RuntimeError(f"e2eekey_create_channel 失敗: {r['error']}")
    channel_ltsm_id = r['ok']

    plaintext_json = json.dumps({'text': text})
    r = await page.evaluate(_ENCRYPT_V2_JS,
                            [channel_ltsm_id, to, from_mid,
                             sender_key_id, receiver_key_id, seq_num, plaintext_json])
    if 'error' in r:
        raise RuntimeError(f"e2eechannel_encrypt_v2 失敗: {r['error']}")
    return r['ok']
