# /// script
# dependencies = ["playwright", "cryptography"]
# ///
"""
download_file.py - 下載並解密 LINE E2EE V2 檔案訊息

流程：
  1. 解密 chunks → {"keyMaterial": "<base64-32bytes>"}
  2. HKDF(SHA-256, keyMaterial, info="FileEncryption") → encKey + macKey + nonce
  3. 建立 X-Talk-Meta 標頭（Thrift 編碼 messageId）
  4. GET obs.line-apps.com/r/talk/emf/<OID>
  5. 驗證 single HMAC-SHA256，AES-CTR 解密
  6. 儲存原始檔名（取自 contentMetadata.FILE_NAME）

用法：
  uv run download_file.py --msg-id <id> --messages messages.json [--out-dir /tmp]
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. _derive_keys(km_b64)            - HKDF 衍生 encKey / macKey / nonce
# 2. _decrypt_file_bytes(data, km)   - 驗證 single HMAC + AES-CTR 解密
# 3. download_file(page, message, out_dir) - 公開入口
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


# ── 1. HKDF 衍生金鑰 ─────────────────────────────────────────────

def _derive_keys(km_b64: str) -> tuple[bytes, bytes, bytes]:
    """HKDF → (encKey[32], macKey[32], nonce[12])"""
    km = base64.b64decode(km_b64)
    hkdf = HKDF(algorithm=hashes.SHA256(), length=76, salt=b'', info=b'FileEncryption')
    derived = hkdf.derive(km)
    return derived[0:32], derived[32:64], derived[64:76]


# ── 2. 解密檔案 bytes ─────────────────────────────────────────────

def _decrypt_file_bytes(data: bytes, km_b64: str) -> bytes:
    """驗證 single HMAC + AES-CTR 解密檔案內容。"""
    enc_key, mac_key, nonce = _derive_keys(km_b64)
    ciphertext, expected_mac = data[:-32], data[-32:]

    actual_mac = hmac_lib.new(mac_key, ciphertext, hashlib.sha256).digest()
    if not hmac_lib.compare_digest(actual_mac, expected_mac):
        raise ValueError("HMAC 驗證失敗，資料可能損毀")

    counter = bytes(nonce) + b'\x00\x00\x00\x00'
    cipher = Cipher(algorithms.AES(enc_key), modes.CTR(counter))
    dec = cipher.decryptor()
    return dec.update(ciphertext) + dec.finalize()


# ── 3. 公開入口 ───────────────────────────────────────────────────

async def download_file(page, message: dict, out_dir: Path) -> Path:
    """
    下載並解密 E2EE V2 檔案訊息，以原始檔名儲存到 out_dir。

    Args:
        page    - Playwright page（LINE extension）
        message - 含 id, chunks, contentMetadata 的訊息 dict
        out_dir - 輸出目錄

    Returns:
        實際寫入的 Path
    """
    meta     = message.get('contentMetadata') or {}
    sid      = meta.get('SID', 'emf')
    oid      = meta.get('OID', message['id'])
    filename = meta.get('FILE_NAME') or f"{message['id']}.bin"
    path     = f"/r/talk/{sid}/{oid}"

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

    print(">>> 解密檔案內容...", flush=True)
    file_bytes = _decrypt_file_bytes(data, km_b64)
    print(f"    解密後 {len(file_bytes)} bytes", flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(file_bytes)
    print(f">>> 已儲存至 {out_path}", flush=True)
    return out_path


# ── 4. 主程式 ─────────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Download LINE E2EE V2 file")
    p.add_argument("--msg-id",   required=True, help="訊息 ID")
    p.add_argument("--messages", default="messages.json", help="messages.json 路徑")
    p.add_argument("--out-dir",  default=None, help="輸出目錄（預設：腳本同目錄）")
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

    out_dir = Path(args.out_dir) if args.out_dir else Path(__file__).parent

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        await download_file(page, message, out_dir)
        try:
            await b.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
