# /// script
# dependencies = ["playwright"]
# ///
"""
encrypt_e2ee.py - LINE E2EE V2 加密（透過 ltsmSandbox postMessage，無需 UI）

流程：
  1. decrypt_with_storage_key(blob) → ltsmKeyId（第二次呼叫時直接回傳整數）
  2. e2eekey_create_channel(ltsmKeyId, recipientPubKeyBytes) → channelLtsmId
  3. e2eechannel_encrypt_v2(channelLtsmId, ...) → raw bytes → vL chunks

公開函式：
  encrypt_message(page, to, from_mid, sender_key_id, receiver_key_id,
                  receiver_pub_key_b64, seq_num, plaintext_json) -> list[str]

  plaintext_json：完整 JSON 字串（文字: {"text":"…"}，圖片: {"keyMaterial":"…"}）

注意：decrypt_with_storage_key 同時執行解密與金鑰載入（wasm 初始化副作用）。
     第一次呼叫（get_my_info）回傳 JSON 並載入金鑰；
     第二次呼叫（_load_my_key）金鑰已在 wasm，直接回傳 ltsmKeyId（整數）。
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. _load_my_key(page, mid, key_id) - decrypt_with_storage_key → ltsmKeyId
# 2. encrypt_message(...)            - 公開入口

import asyncio
import json

_SANDBOX_JS = """(data) => new Promise((resolve) => {
    const iframe = document.querySelector("iframe[src*='ltsmSandbox']");
    if (!iframe) { resolve({error: "no iframe"}); return; }
    const sandboxId = new URL(iframe.src).searchParams.get("sandboxId");
    // 先等 40ms 讓殘留訊息散盡，再安裝 handler；decrypt_with_storage_key 回傳字串，過濾非字串
    setTimeout(() => {
        const handler = (evt) => {
            const d = evt.data;
            if (d && d.sandboxId === sandboxId &&
                (d.type === "response" || d.type === "error")) {
                // decrypt_with_storage_key 回傳 JSON，必須以 '{' 開頭；base64 或空字串是 stale
                if (d.type === "response" && (typeof d.data !== "string" || !d.data.startsWith('{'))) return;
                window.removeEventListener("message", handler);
                resolve(d.type === "response" ? {ok: d.data} : {error: String(d.data)});
            }
        };
        window.addEventListener("message", handler);
        iframe.contentWindow.postMessage({sandboxId, type: "request", data}, "*");
        setTimeout(() => resolve({error: "timeout"}), 8000);
    }, 40);
})"""

_FIND_KEY_JS = """([targetKeyId]) => new Promise((resolve) => {
    // 掃描 pS map：用 e2eekey_get_key_id 找 extension 已載入且 keyId==targetKeyId 的 ltsmKeyId
    // LINE keyId 是數百萬級大整數；ltsmKeyId 是小整數（1, 2, 3...），以此區分 stale messages
    const iframe = document.querySelector("iframe[src*='ltsmSandbox']");
    if (!iframe) { resolve({error: "no iframe"}); return; }
    const sandboxId = new URL(iframe.src).searchParams.get("sandboxId");
    let currentId = 0;

    const next = () => {
        currentId++;
        if (currentId > 50) { resolve({error: "key not found in first 50 slots"}); return; }
        iframe.contentWindow.postMessage({sandboxId, type: "request",
            data: {command: "e2eekey_get_key_id", ltsmKeyId: currentId}}, "*");
    };

    const handler = (evt) => {
        const d = evt.data;
        if (!d || d.sandboxId !== sandboxId) return;
        if (d.type === "response" && typeof d.data === "number") {
            if (d.data < 1000) return;  // stale ltsmKeyId response，忽略
            if (d.data === targetKeyId) {
                window.removeEventListener("message", handler);
                resolve({ok: currentId});
            } else {
                next();
            }
        } else if (d.type === "error") {
            next();  // 此 slot 不存在，繼續
        }
    };

    window.addEventListener("message", handler);
    setTimeout(next, 40);  // 40ms drain
    setTimeout(() => { window.removeEventListener("message", handler); resolve({error: "scan timeout"}); }, 10000);
})"""

_CREATE_CHANNEL_JS = """([keyId, pubB64]) => new Promise((resolve) => {
    const iframe = document.querySelector("iframe[src*='ltsmSandbox']");
    if (!iframe) { resolve({error: "no iframe"}); return; }
    const sandboxId = new URL(iframe.src).searchParams.get("sandboxId");
    const payload = Uint8Array.from(atob(pubB64), c => c.charCodeAt(0));
    // 先等 40ms，讓前序 sandbox 操作的殘留訊息散盡，再安裝 handler
    setTimeout(() => {
        const handler = (evt) => {
            const d = evt.data;
            if (d && d.sandboxId === sandboxId &&
                (d.type === "response" || d.type === "error")) {
                // e2eekey_create_channel 回傳整數 channelLtsmId，過濾非整數回應（stale messages）
                if (d.type === "response" && typeof d.data !== "number") return;
                window.removeEventListener("message", handler);
                resolve(d.type === "response" ? {ok: d.data} : {error: String(d.data)});
            }
        };
        window.addEventListener("message", handler);
        iframe.contentWindow.postMessage({sandboxId, type: "request",
            data: {command: "e2eekey_create_channel", ltsmKeyId: keyId, payload}}, "*");
        setTimeout(() => resolve({error: "timeout"}), 8000);
    }, 40);
})"""

_ENCRYPT_V2_JS = """([chId, to, frm, sKId, rKId, ctType, seqN, pt]) => new Promise((resolve) => {
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
    // 先等 40ms，讓前序 sandbox 操作的殘留訊息散盡，再安裝 handler
    setTimeout(() => {
        const handler = (evt) => {
            const d = evt.data;
            if (d && d.sandboxId === sandboxId &&
                (d.type === "response" || d.type === "error")) {
                // e2eechannel_encrypt_v2 回傳 ArrayBuffer 或 Uint8Array，過濾非 binary 回應（stale messages）
                if (d.type === "response" && !(d.data instanceof ArrayBuffer) && !ArrayBuffer.isView(d.data)) return;
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
                             contentType: ctType, sequenceNumber: BigInt(seqN), plaintext: ptBytes}}}, "*");
        setTimeout(() => resolve({error: "timeout"}), 8000);
    }, 40);
})"""


# ── 1. 載入私鑰 ───────────────────────────────────────────────────

async def _load_my_key(page, my_mid: str, sender_key_id: int) -> int:
    """找到 extension 已載入的私鑰 ltsmKeyId（用 e2eekey_get_key_id 掃描）。"""
    r = await page.evaluate(_FIND_KEY_JS, [sender_key_id])
    if 'error' in r:
        raise RuntimeError(f"找不到 senderKeyId {sender_key_id} 的 ltsmKeyId: {r['error']}")
    return r['ok']


# ── 2. 公開入口 ───────────────────────────────────────────────────

async def encrypt_message(page,
                          to: str, from_mid: str,
                          sender_key_id: int, receiver_key_id: int,
                          receiver_pub_key_b64: str,
                          seq_num: int, plaintext_json: str,
                          content_type: int = 0) -> list:
    """
    E2EE V2 加密訊息，回傳 5 個 base64 chunks。

    Args:
        page               - Playwright page（LINE extension）
        to                 - 收件人 mid
        from_mid           - 我的 mid
        sender_key_id      - 我的 E2EE key id（int）
        receiver_key_id    - 對方 E2EE key id（int）
        receiver_pub_key_b64 - 對方 Curve25519 公鑰（base64）
        seq_num            - 訊息 sequence number
        plaintext_json     - 完整明文 JSON（文字: {"text":"…"}，圖片: {"keyMaterial":"…"}）
    """
    key_ltsm_id = await _load_my_key(page, from_mid, sender_key_id)

    r = await page.evaluate(_CREATE_CHANNEL_JS, [key_ltsm_id, receiver_pub_key_b64])
    if 'error' in r:
        raise RuntimeError(f"e2eekey_create_channel 失敗: {r['error']}")
    channel_ltsm_id = r['ok']

    r = await page.evaluate(_ENCRYPT_V2_JS,
                            [channel_ltsm_id, to, from_mid,
                             sender_key_id, receiver_key_id, content_type, seq_num, plaintext_json])
    if 'error' in r:
        raise RuntimeError(f"e2eechannel_encrypt_v2 失敗: {r['error']}")
    return r['ok']
