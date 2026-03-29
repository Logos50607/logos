# /// script
# dependencies = ["playwright", "cryptography"]
# ///
"""
download_video.py - 下載並解密 LINE E2EE V2 影片訊息

流程：
  1. 解密 chunks → {"keyMaterial": "<base64-32bytes>"}
  2. HKDF(SHA-256, keyMaterial, info="FileEncryption") → encKey + macKey + nonce
  3. 建立 X-Talk-Meta 標頭（Thrift 編碼 messageId）
  4. GET obs.line-apps.com/r/talk/emv/<OID>
  5. 驗證 chunked HMAC-SHA256，AES-CTR 解密

用法：
  uv run download_video.py --msg-id <id> --messages messages.json --out out.mp4
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. _derive_keys(km_b64)             - HKDF 衍生 encKey / macKey / nonce
# 2. _decrypt_video_bytes(data, km)   - 驗證 chunked HMAC + AES-CTR 解密
# 3. download_video(page, message, out_path) - 公開入口
# 4. main（standalone）

import argparse
import asyncio
import base64
import hashlib
import hmac as hmac_lib
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from gw_client import CDP_URL, find_ext_page, get_access_token, get_obs_token
from decrypt_e2ee import decrypt_chunks
from download_image import build_talk_meta, _obs_download

_CHUNK_SIZE = 131072  # 128KB


# ── 1. HKDF 衍生金鑰 ─────────────────────────────────────────────

def _derive_keys(km_b64: str) -> tuple[bytes, bytes, bytes]:
    """HKDF → (encKey[32], macKey[32], nonce[12])"""
    km = base64.b64decode(km_b64)
    hkdf = HKDF(algorithm=hashes.SHA256(), length=76, salt=b'', info=b'FileEncryption')
    derived = hkdf.derive(km)
    return derived[0:32], derived[32:64], derived[64:76]


# ── 2. 解密影片 bytes ─────────────────────────────────────────────

def _decrypt_video_bytes(data: bytes, km_b64: str) -> bytes:
    """驗證 chunked HMAC + AES-CTR 解密影片內容。"""
    enc_key, mac_key, nonce = _derive_keys(km_b64)
    ciphertext, expected_mac = data[:-32], data[-32:]

    # 影片使用 chunked HMAC：HMAC-SHA256(macKey, concat(SHA-256(每個 128KB)))
    chunk_hashes = b''.join(
        hashlib.sha256(ciphertext[i:i + _CHUNK_SIZE]).digest()
        for i in range(0, len(ciphertext), _CHUNK_SIZE)
    )
    actual_mac = hmac_lib.new(mac_key, chunk_hashes, hashlib.sha256).digest()
    if not hmac_lib.compare_digest(actual_mac, expected_mac):
        raise ValueError("chunked HMAC 驗證失敗，資料可能損毀")

    counter = bytes(nonce) + b'\x00\x00\x00\x00'
    cipher = Cipher(algorithms.AES(enc_key), modes.CTR(counter))
    dec = cipher.decryptor()
    return dec.update(ciphertext) + dec.finalize()


# ── 3. 公開入口 ───────────────────────────────────────────────────

async def download_video(page, message: dict, out_path: Path) -> Path:
    """
    下載並解密 E2EE V2 影片訊息，儲存到 out_path。

    Args:
        page     - Playwright page（LINE extension）
        message  - 含 id, chunks, contentMetadata 的訊息 dict
        out_path - 輸出檔案路徑（.mp4 等）

    Returns:
        實際寫入的 Path
    """
    meta = message.get('contentMetadata') or {}
    sid  = meta.get('SID', 'emv')
    oid  = meta.get('OID', message['id'])
    path = f"/r/talk/{sid}/{oid}"

    print(">>> 取得 token...", flush=True)
    token = await get_access_token(page)

    print(">>> 解密 chunks...", flush=True)
    plaintext = await decrypt_chunks(page, token, message)
    km_b64 = plaintext.get('keyMaterial')
    if not km_b64:
        raise RuntimeError(f"chunks 解密結果沒有 keyMaterial: {plaintext}")

    print(">>> 取得 OBS token...", flush=True)
    obs_token = await get_obs_token(page, token)

    talk_meta = build_talk_meta(message['id'])
    print(f">>> 下載 {path}...", flush=True)
    data = _obs_download(path, obs_token, talk_meta)
    print(f"    下載 {len(data)} bytes", flush=True)

    print(">>> 解密影片內容（chunked HMAC）...", flush=True)
    video_bytes = _decrypt_video_bytes(data, km_b64)
    print(f"    解密後 {len(video_bytes)} bytes", flush=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(video_bytes)
    print(f">>> 已儲存至 {out_path}", flush=True)
    return out_path


# ── 4. 主程式 ─────────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Download LINE E2EE V2 video")
    p.add_argument("--msg-id",   required=True, help="訊息 ID")
    p.add_argument("--messages", default="messages.json", help="messages.json 路徑")
    p.add_argument("--out",      default=None, help="輸出路徑（預設: <msg-id>.mp4）")
    args = p.parse_args()

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

    out = Path(args.out) if args.out else Path(__file__).parent / f"{args.msg_id}.mp4"

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        await download_video(page, message, out)
        try:
            await b.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
