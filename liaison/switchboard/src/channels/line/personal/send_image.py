# /// script
# dependencies = ["playwright", "cryptography"]
# ///
"""
send_image.py - 透過 LINE GW API（E2EE V2）發送圖片訊息

流程：
  1. 生成 32-byte keyMaterial（隨機）
  2. HKDF(SHA-256, km, "FileEncryption") → encKey / macKey / nonce
  3. AES-CTR 加密圖片 + HMAC-SHA256 附加
  4. POST 加密圖片至 OBS（/r/talk/emi/reqid-<rand>）
  5. 從回應標頭取得 x-obs-oid（實際 OID）
  6. E2EE 加密 {"keyMaterial": km_b64} 為 chunks（同文字訊息）
  7. 呼叫 sendMessage API（contentType=1, SID=emi, OID=x-obs-oid）

用法：
  uv run send_image.py --to <mid> --file image.jpg
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. _generate_km()            - 生成隨機 keyMaterial
# 2. _encrypt_image(data, km)  - HKDF + AES-CTR + HMAC
# 3. _obs_upload(...)          - POST 加密圖片至 OBS
# 4. _build_send_body(...)     - 組 sendMessage body
# 5. send_image(page, to, file_path) - 完整流程
# 6. main（standalone）

import argparse
import asyncio
import base64
import hashlib
import hmac as hmac_lib
import json
import os
import struct
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


# ── 1. 生成隨機 keyMaterial ──────────────────────────────────────

def _generate_km() -> tuple[str, bytes]:
    """回傳 (km_b64, km_bytes)。"""
    km = os.urandom(32)
    return base64.b64encode(km).decode(), km


def _get_image_size(data: bytes, extension: str) -> tuple[int, int]:
    """從圖片原始 bytes 取得 (width, height)，失敗回傳 (0, 0)。"""
    try:
        if extension == 'png' and data[:8] == b'\x89PNG\r\n\x1a\n':
            return struct.unpack('>II', data[16:24])
        if extension in ('jpg', 'jpeg'):
            i = 2
            while i + 4 < len(data):
                if data[i] != 0xFF:
                    break
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack('>HH', data[i + 5:i + 9])
                    return w, h
                seg_len = struct.unpack('>H', data[i + 2:i + 4])[0]
                i += 2 + seg_len
    except Exception:
        pass
    return 0, 0


# ── 2. 加密圖片 ───────────────────────────────────────────────────

def _encrypt_image(data: bytes, km_b64: str) -> bytes:
    """HKDF 衍生金鑰，AES-CTR 加密，附加 HMAC-SHA256。"""
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


# ── 3. 上傳至 OBS ────────────────────────────────────────────────

def _obs_post(obs_token: str, enc_data: bytes, path: str,
              filename: str) -> str:
    """
    POST 加密資料至 OBS 指定路徑，回傳 x-obs-oid 標頭（可能為空）。
    """
    import http.client, ssl
    obs_params = base64.urlsafe_b64encode(
        json.dumps({"ver": "2.0", "name": filename, "type": "file"}).encode()
    ).rstrip(b'=').decode()

    parsed = urllib.parse.urlparse(_OBS_BASE + path)
    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection(parsed.netloc, context=ctx, timeout=60)
    try:
        conn.request('POST', parsed.path, body=enc_data, headers={
            'X-Line-Access':       obs_token,
            'X-Line-Application':  'CHROMEOS\t3.7.2\tChrome_OS\t',
            'X-Obs-Params':        obs_params,
            'Content-Type':        'application/octet-stream',
            'Content-Length':      str(len(enc_data)),
            'Origin':  f'chrome-extension://{EXT_ID}',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        })
        resp = conn.getresponse()
        resp.read()
        if resp.status not in (200, 201):
            raise RuntimeError(f"OBS 上傳失敗 HTTP {resp.status}: {path}")
        return resp.getheader('x-obs-oid', '')
    finally:
        conn.close()


def _obs_upload(obs_token: str, enc_data: bytes,
                filename: str, file_size: int) -> str:
    """
    POST 加密圖片至 OBS，回傳伺服器分配的 OID（x-obs-oid 標頭）。
    上傳完成後自動補傳 ud-preview（同資料），讓 mobile client 可以顯示。
    """
    reqid = f"reqid-{uuid.uuid4()}"
    oid = _obs_post(obs_token, enc_data, f"/r/talk/emi/{reqid}", filename)
    if not oid:
        raise RuntimeError("OBS 上傳回應沒有 x-obs-oid 標頭")

    # 上傳 preview（mobile app 需要此才能顯示縮圖並允許點擊）
    try:
        _obs_post(obs_token, enc_data, f"/r/talk/emi/{oid}__ud-preview", filename)
        print("    preview 上傳完成", flush=True)
    except Exception as e:
        print(f"    preview 上傳失敗（忽略）: {e}", flush=True)

    return oid


# ── 4. 組 sendMessage body ────────────────────────────────────────

def _build_send_body(seq_num: int, to: str, my_mid: str,
                     oid: str, file_size: int, chunks: list,
                     extension: str = "jpeg",
                     width: int = 0, height: int = 0) -> list:
    """組 sendMessage API body（contentType=1 圖片）。"""
    meta = {
        "onObs": True, "category": "original",
        "animated": False, "extension": extension,
        "fileSize": file_size,
    }
    if width and height:
        meta["width"] = width
        meta["height"] = height
    content_meta = {
        "e2eeVersion": "2",
        "SID": "emi",
        "OID": oid,
        "FILE_SIZE": str(file_size),
        "MEDIA_CONTENT_INFO": json.dumps(meta),
    }
    if width and height:
        content_meta["MEDIA_THUMB_INFO"] = json.dumps({"width": width, "height": height})
    return [seq_num, {
        "from": my_mid, "to": to, "toType": 0,
        "id": f"local-{seq_num}", "contentType": 1,
        "contentMetadata": content_meta,
        "hasContent": True,
        "chunks": chunks,
    }]


# ── 5. 完整流程 ───────────────────────────────────────────────────

async def send_image(page, to: str, file_path: Path) -> dict:
    """
    發送 E2EE V2 圖片訊息。

    Args:
        page      - Playwright page（LINE extension）
        to        - 目標 mid
        file_path - 本機圖片路徑

    Returns:
        {'ok': True, 'seq': <int>}  或  {'error': '...'}
    """
    img_data = file_path.read_bytes()
    file_size = len(img_data)
    filename  = file_path.name

    print(">>> 取得 token...", flush=True)
    token = await get_access_token(page)

    print(">>> 取得我的 key...", flush=True)
    my_mid, sender_key_id = await get_my_info(page)

    print(">>> 取得對方公鑰...", flush=True)
    receiver_key_id, receiver_pub_b64 = await get_recipient_key(page, token, to)

    print(">>> 生成 keyMaterial...", flush=True)
    km_b64, _ = _generate_km()

    print(">>> 加密圖片...", flush=True)
    enc_data = _encrypt_image(img_data, km_b64)
    print(f"    明文 {file_size} bytes → 加密後 {len(enc_data)} bytes", flush=True)

    print(">>> 取得 OBS token...", flush=True)
    obs_token = await get_obs_token(page, token)

    print(">>> 上傳至 OBS...", flush=True)
    oid = _obs_upload(obs_token, enc_data, filename, file_size)
    print(f"    OID={oid[:40]}...", flush=True)

    print(">>> E2EE 加密 keyMaterial...", flush=True)
    seq_num  = int(time.time() * 1000) & 0x7FFFFFFF
    plaintext = json.dumps({"keyMaterial": km_b64})
    chunks   = await encrypt_message(page, to, my_mid,
                                     sender_key_id, receiver_key_id,
                                     receiver_pub_b64, seq_num,
                                     plaintext, content_type=1)

    print(">>> 發送訊息...", flush=True)
    ext = file_path.suffix.lstrip('.').lower() or "jpeg"
    w, h = _get_image_size(img_data, ext)
    print(f"    尺寸: {w}x{h}", flush=True)
    body_obj = _build_send_body(seq_num, to, my_mid, oid, file_size, chunks, ext, w, h)
    body_str = json.dumps(body_obj)
    hmac_val = await compute_hmac(page, token, _PATH_SEND, body_str)
    result   = call_api(_PATH_SEND, body_obj, token, hmac_val)

    if result.get('code') == 0:
        return {'ok': True, 'seq': seq_num}
    return {'error': f"sendMessage 失敗: {result}"}


# ── 6. 主程式 ─────────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Send LINE image via GW API (E2EE V2)")
    p.add_argument("--to",   required=True, help="目標 mid")
    p.add_argument("--file", required=True, help="圖片路徑")
    args = p.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"找不到檔案: {file_path}", file=sys.stderr)
        sys.exit(1)

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        result = await send_image(page, args.to, file_path)
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
