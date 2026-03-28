# /// script
# dependencies = ["playwright", "cryptography"]
# ///
"""
download_image.py - 下載並解密 LINE E2EE V2 圖片訊息

流程：
  1. 解密 chunks → {"keyMaterial": "<base64-32bytes>"}
  2. HKDF(SHA-256, keyMaterial, info="FileEncryption") → encKey + macKey + nonce
  3. 建立 X-Talk-Meta 標頭（Thrift 編碼 messageId）
  4. GET obs.line-apps.com/r/talk/<SID>/<OID>（X-Line-Access + X-Talk-Meta）
  5. 驗證 HMAC-SHA256，AES-CTR 解密

用法：
  uv run download_image.py --msg-id <id> --messages messages.json --out out.jpg
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. build_talk_meta(msg_id)          - 組 X-Talk-Meta 標頭
# 2. _derive_keys(km_b64)             - HKDF 衍生 encKey / macKey / nonce
# 3. _decrypt_image_bytes(data, km)   - 驗證 HMAC + AES-CTR 解密
# 4. _obs_download(path, token, meta) - 下載 OBS 內容
# 5. download_image(page, message, out_path) - 公開入口
# 6. main（standalone）

import argparse
import asyncio
import base64
import hashlib
import hmac as hmac_lib
import json
import struct
import sys
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from gw_client import CDP_URL, GW_BASE, find_ext_page, get_access_token, get_obs_token
from decrypt_e2ee import decrypt_chunks

_OBS_BASE = "https://obs.line-apps.com"


# ── 1. 組 X-Talk-Meta ────────────────────────────────────────────

def build_talk_meta(msg_id: str) -> str:
    """
    Thrift 編碼 messageId，包裝為 JSON，再做 base64url 編碼。
    結果用作 X-Talk-Meta 標頭。
    """
    mid_bytes = msg_id.encode('utf-8')
    buf = bytearray()
    buf.append(11)                            # field type: STRING
    buf += struct.pack('>H', 4)               # field id: 4
    buf += struct.pack('>I', len(mid_bytes))  # string length
    buf += mid_bytes
    buf.append(15)                            # field type: LIST
    buf += struct.pack('>H', 27)              # field id: 27
    buf.append(12)                            # element type: STRUCT
    buf += struct.pack('>I', 0)               # count: 0
    buf.append(0)                             # STOP byte

    msg_b64 = base64.b64encode(bytes(buf)).decode()
    json_str = json.dumps({"message": msg_b64})
    return base64.urlsafe_b64encode(json_str.encode()).rstrip(b'=').decode()


# ── 2. HKDF 衍生金鑰 ─────────────────────────────────────────────

def _derive_keys(km_b64: str) -> tuple[bytes, bytes, bytes]:
    """HKDF → (encKey[32], macKey[32], nonce[12])"""
    km = base64.b64decode(km_b64)
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=76,
        salt=b'',
        info=b'FileEncryption',
    )
    derived = hkdf.derive(km)
    return derived[0:32], derived[32:64], derived[64:76]


# ── 3. 解密圖片 bytes ─────────────────────────────────────────────

def _decrypt_image_bytes(data: bytes, km_b64: str) -> bytes:
    """驗證 HMAC + AES-CTR 解密圖片內容。"""
    enc_key, mac_key, nonce = _derive_keys(km_b64)
    ciphertext, expected_mac = data[:-32], data[-32:]

    actual_mac = hmac_lib.new(mac_key, ciphertext, hashlib.sha256).digest()
    if not hmac_lib.compare_digest(actual_mac, expected_mac):
        raise ValueError("HMAC 驗證失敗，資料可能損毀")

    counter = bytes(nonce) + b'\x00\x00\x00\x00'   # 16 bytes
    cipher = Cipher(algorithms.AES(enc_key), modes.CTR(counter))
    dec = cipher.decryptor()
    return dec.update(ciphertext) + dec.finalize()


# ── 4. 下載 OBS 內容 ─────────────────────────────────────────────

def _obs_download(path: str, obs_token: str, talk_meta: str) -> bytes:
    """GET obs.line-apps.com<path>，回傳原始 bytes。"""
    url = _OBS_BASE + path
    req = urllib.request.Request(url, headers={
        'x-line-access':       obs_token,
        'x-line-application':  'CHROMEOS\t3.7.2\tChrome_OS\t',
        'x-talk-meta':         talk_meta,
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


# ── 5. 公開入口 ───────────────────────────────────────────────────

async def download_image(page, message: dict, out_path: Path) -> Path:
    """
    下載並解密 E2EE V2 圖片訊息，儲存到 out_path。

    Args:
        page     - Playwright page（LINE extension）
        message  - 含 id, from, to, contentType, chunks, contentMetadata 的訊息 dict
        out_path - 輸出檔案路徑（.jpg / .png 等）

    Returns:
        實際寫入的 Path
    """
    meta = message.get('contentMetadata') or {}
    sid  = meta.get('SID', 'm')
    oid  = meta.get('OID', message['id'])
    path = f"/r/talk/{sid}/{oid}"

    print(f">>> 取得 token...", flush=True)
    token = await get_access_token(page)

    print(f">>> 解密 chunks...", flush=True)
    plaintext = await decrypt_chunks(page, token, message)
    km_b64 = plaintext.get('keyMaterial')
    if not km_b64:
        raise RuntimeError(f"chunks 解密結果沒有 keyMaterial: {plaintext}")
    print(f"    keyMaterial 長度={len(base64.b64decode(km_b64))} bytes", flush=True)

    print(f">>> 取得 OBS token...", flush=True)
    obs_token = await get_obs_token(page, token)

    talk_meta = build_talk_meta(message['id'])
    print(f">>> 下載 {path}...", flush=True)
    data = _obs_download(path, obs_token, talk_meta)
    print(f"    下載 {len(data)} bytes", flush=True)

    print(f">>> 解密圖片內容...", flush=True)
    img_bytes = _decrypt_image_bytes(data, km_b64)
    print(f"    解密後 {len(img_bytes)} bytes", flush=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(img_bytes)
    print(f">>> 已儲存至 {out_path}", flush=True)
    return out_path


# ── 6. 主程式 ─────────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Download LINE E2EE image")
    p.add_argument("--msg-id",   required=True, help="訊息 ID")
    p.add_argument("--messages", default="messages.json", help="messages.json 路徑")
    p.add_argument("--out",      default=None,  help="輸出路徑（預設: <msg-id>.jpg）")
    args = p.parse_args()

    # 從 messages.json 找訊息
    msgs_path = Path(args.messages)
    if not msgs_path.is_absolute():
        msgs_path = Path(__file__).parent / msgs_path
    data = json.loads(msgs_path.read_text())
    message = None
    if isinstance(data, dict):
        for msgs in data.values():
            for m in msgs:
                if isinstance(m, dict) and m.get('id') == args.msg_id:
                    message = m
                    break
            if message:
                break
    elif isinstance(data, list):
        for m in data:
            if isinstance(m, dict) and m.get('id') == args.msg_id:
                message = m
                break

    if not message:
        print(f"找不到 msg-id={args.msg_id}", file=sys.stderr)
        sys.exit(1)

    meta = message.get('contentMetadata') or {}
    ext  = json.loads(meta.get('MEDIA_CONTENT_INFO', '{}')).get('extension', 'jpg')
    out  = Path(args.out) if args.out else Path(__file__).parent / f"{args.msg_id}.{ext}"

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        await download_image(page, message, out)
        try:
            await b.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
