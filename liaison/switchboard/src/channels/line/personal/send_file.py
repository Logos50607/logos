# /// script
# dependencies = ["playwright", "cryptography"]
# ///
"""
send_file.py - 透過 LINE GW API（E2EE V2）發送任意檔案

流程：
  1. 生成 32-byte keyMaterial（隨機）
  2. HKDF(SHA-256, km, "FileEncryption") → encKey / macKey / nonce
  3. AES-CTR 加密 + HMAC-SHA256（single，非 chunked）
  4. POST 加密檔案至 OBS（/r/talk/emf/reqid-<rand>）
  5. 從回應標頭取得 x-obs-oid
  6. E2EE 加密 {"keyMaterial": km_b64} 為 chunks
  7. 呼叫 sendMessage API（contentType=14, SID=emf）

用法：
  uv run send_file.py --to <mid> --file document.pdf
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. _encrypt_file(data, km_b64)  - HKDF + AES-CTR + single HMAC
# 2. _obs_upload(...)             - POST 加密檔案至 OBS /r/talk/emf/
# 3. _build_send_body(...)        - 組 sendMessage body
# 4. send_file(page, to, path)    - 完整流程
# 5. main（standalone）

import argparse
import asyncio
import base64
import hashlib
import hmac as hmac_lib
import json
import os
import sys
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from gw_client import (CDP_URL, GW_BASE, EXT_ID, find_ext_page,
                       get_access_token, get_obs_token, compute_hmac, call_api)
from encrypt_e2ee import encrypt_message
from send_api import get_my_info, get_recipient_key

_PATH_SEND = "/api/talk/thrift/Talk/TalkService/sendMessage"
_OBS_BASE  = "https://obs.line-apps.com"
_CT_FILE   = 14  # EU.FILE


# ── 1. 加密 ───────────────────────────────────────────────────────

def _encrypt_file(data: bytes, km_b64: str) -> bytes:
    """HKDF 衍生金鑰，AES-CTR 加密，附加 single HMAC-SHA256。"""
    km = base64.b64decode(km_b64)
    hkdf = HKDF(algorithm=hashes.SHA256(), length=76, salt=b'', info=b'FileEncryption')
    derived = hkdf.derive(km)
    enc_key, mac_key, nonce = derived[0:32], derived[32:64], derived[64:76]

    counter = bytes(nonce) + b'\x00\x00\x00\x00'
    cipher = Cipher(algorithms.AES(enc_key), modes.CTR(counter))
    enc = cipher.encryptor()
    ciphertext = enc.update(data) + enc.finalize()
    mac = hmac_lib.new(mac_key, ciphertext, hashlib.sha256).digest()
    return ciphertext + mac


# ── 2. 上傳至 OBS ─────────────────────────────────────────────────

def _obs_upload(obs_token: str, enc_data: bytes, filename: str) -> str:
    """POST 加密檔案至 /r/talk/emf/，回傳 OID。"""
    import http.client, ssl
    obs_params = base64.urlsafe_b64encode(
        json.dumps({"ver": "2.0", "name": filename, "type": "file"}).encode()
    ).rstrip(b'=').decode()

    reqid = f"reqid-{uuid.uuid4()}"
    path  = f"/r/talk/emf/{reqid}"
    parsed = urllib.parse.urlparse(_OBS_BASE + path)
    ctx  = ssl.create_default_context()
    conn = http.client.HTTPSConnection(parsed.netloc, context=ctx, timeout=60)
    try:
        conn.request('POST', parsed.path, body=enc_data, headers={
            'X-Line-Access':      obs_token,
            'X-Line-Application': 'CHROMEOS\t3.7.2\tChrome_OS\t',
            'X-Obs-Params':       obs_params,
            'Content-Type':       'application/octet-stream',
            'Content-Length':     str(len(enc_data)),
            'Origin':  f'chrome-extension://{EXT_ID}',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        })
        resp = conn.getresponse()
        resp.read()
        if resp.status not in (200, 201):
            raise RuntimeError(f"OBS 上傳失敗 HTTP {resp.status}")
        oid = resp.getheader('x-obs-oid', '')
        if not oid:
            raise RuntimeError("OBS 回應沒有 x-obs-oid 標頭")
        return oid
    finally:
        conn.close()


# ── 3. 組 sendMessage body ────────────────────────────────────────

def _build_send_body(seq_num: int, to: str, my_mid: str,
                     oid: str, file_size: int, filename: str,
                     chunks: list) -> list:
    """組 sendMessage API body（contentType=14 檔案）。"""
    return [seq_num, {
        "from": my_mid, "to": to, "toType": 0,
        "id": f"local-{seq_num}", "contentType": _CT_FILE,
        "contentMetadata": {
            "e2eeVersion": "2",
            "SID": "emf",
            "OID": oid,
            "FILE_SIZE": str(file_size),
            "FILE_NAME": filename,
        },
        "hasContent": True,
        "chunks": chunks,
    }]


# ── 4. 完整流程 ───────────────────────────────────────────────────

async def send_file(page, to: str, file_path: Path) -> dict:
    """
    發送 E2EE V2 檔案訊息。

    Args:
        page      - Playwright page（LINE extension）
        to        - 目標 mid
        file_path - 本機檔案路徑

    Returns:
        {'ok': True, 'seq': <int>}  或  {'error': '...'}
    """
    data      = file_path.read_bytes()
    file_size = len(data)
    filename  = file_path.name

    print(">>> 取得 token...", flush=True)
    token = await get_access_token(page)

    print(">>> 取得我的 key...", flush=True)
    my_mid, sender_key_id = await get_my_info(page)

    print(">>> 取得對方公鑰...", flush=True)
    receiver_key_id, receiver_pub_b64 = await get_recipient_key(page, token, to)

    print(">>> 加密檔案...", flush=True)
    enc_data = _encrypt_file(data, km_b64 := base64.b64encode(os.urandom(32)).decode())
    print(f"    {filename}  {file_size} bytes → 加密後 {len(enc_data)} bytes", flush=True)

    print(">>> 取得 OBS token...", flush=True)
    obs_token = await get_obs_token(page, token)

    print(">>> 上傳至 OBS...", flush=True)
    oid = _obs_upload(obs_token, enc_data, filename)
    print(f"    OID={oid[:40]}...", flush=True)

    print(">>> E2EE 加密 keyMaterial...", flush=True)
    seq_num   = int(time.time() * 1000) & 0x7FFFFFFF
    plaintext = json.dumps({"keyMaterial": km_b64})
    chunks    = await encrypt_message(page, to, my_mid,
                                      sender_key_id, receiver_key_id,
                                      receiver_pub_b64, seq_num,
                                      plaintext, content_type=_CT_FILE)

    print(">>> 發送訊息...", flush=True)
    body_obj = _build_send_body(seq_num, to, my_mid, oid, file_size, filename, chunks)
    body_str = json.dumps(body_obj)
    hmac_val = await compute_hmac(page, token, _PATH_SEND, body_str)
    result   = call_api(_PATH_SEND, body_obj, token, hmac_val)

    if result.get('code') == 0:
        return {'ok': True, 'seq': seq_num}
    return {'error': f"sendMessage 失敗: {result}"}


# ── 5. 主程式 ─────────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Send LINE file via GW API (E2EE V2)")
    p.add_argument("--to",   required=True, help="目標 mid")
    p.add_argument("--file", required=True, help="檔案路徑")
    args = p.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"找不到檔案: {file_path}", file=sys.stderr)
        sys.exit(1)

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        result = await send_file(page, args.to, file_path)
        if result.get('ok'):
            print(f">>> 成功 seq={result['seq']}", flush=True)
        else:
            print(f">>> 失敗: {result['error']}", flush=True)
        try:
            await b.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
