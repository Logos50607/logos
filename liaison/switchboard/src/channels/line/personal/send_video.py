# /// script
# dependencies = ["playwright", "cryptography", "av"]
# ///
"""
send_video.py - 透過 LINE GW API（E2EE V2）發送影片訊息

流程：
  1. 生成 32-byte keyMaterial（隨機）
  2. HKDF(SHA-256, km, "FileEncryption") → encKey / macKey / nonce
  3. AES-CTR 加密影片 + HMAC-SHA256 附加
  4. POST 加密影片至 OBS（/r/talk/emv/reqid-<rand>）
  5. 從回應標頭取得 x-obs-oid（實際 OID）
  6. 擷取影片第一幀作為縮圖，加密後上傳至 {oid}__ud-preview
  7. E2EE 加密 {"keyMaterial": km_b64} 為 chunks
  8. 呼叫 sendMessage API（contentType=2, SID=emv, OID=x-obs-oid）

用法：
  uv run send_video.py --to <mid> --file video.mp4
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. _generate_km()              - 生成隨機 keyMaterial
# 2. _encrypt_data(data, km)     - HKDF + AES-CTR + HMAC
# 3. _get_video_info(path)       - 取得影片時長（ms）與縮圖幀
# 4. _obs_post(...)              - POST 加密資料至 OBS
# 5. _obs_upload_video(...)      - 上傳影片主體 + 縮圖 preview
# 6. _build_send_body(...)       - 組 sendMessage body
# 7. send_video(page, to, path)  - 完整流程
# 8. main（standalone）

import argparse
import asyncio
import base64
import hashlib
import hmac as hmac_lib
import io
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
_CT_VIDEO  = 2   # EU.VIDEO


# ── 1. 生成隨機 keyMaterial ──────────────────────────────────────

def _generate_km() -> tuple[str, bytes]:
    """回傳 (km_b64, km_bytes)。"""
    km = os.urandom(32)
    return base64.b64encode(km).decode(), km


# ── 2. 加密資料 ───────────────────────────────────────────────────

def _encrypt_data(data: bytes, km_b64: str) -> bytes:
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


# ── 3. 取得影片資訊 ───────────────────────────────────────────────

def _get_video_info(file_path: Path) -> tuple[int, bytes | None, int, int]:
    """
    回傳 (duration_ms, thumb_jpeg_bytes_or_None, thumb_w, thumb_h)。
    使用 PyAV 擷取第一幀。若 av 未安裝則回傳 (0, None, 0, 0)。
    """
    try:
        import av  # type: ignore
        with av.open(str(file_path)) as container:
            # 取得時長
            dur_ms = int(container.duration / 1000) if container.duration else 0

            # 擷取第一幀
            video_stream = next(
                (s for s in container.streams if s.type == 'video'), None
            )
            if video_stream is None:
                return dur_ms, None, 0, 0

            container.seek(0)
            for frame in container.decode(video_stream):
                img = frame.to_image()   # PIL Image
                w, h = img.size
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=85)
                return dur_ms, buf.getvalue(), w, h
    except Exception as e:
        print(f"    無法讀取影片資訊（{e}），使用預設值", flush=True)
    return 0, None, 0, 0


# ── 4. OBS POST ───────────────────────────────────────────────────

def _obs_post(obs_token: str, enc_data: bytes, path: str,
              filename: str, sid: str = "emv") -> str:
    """POST 加密資料至 OBS 指定路徑，回傳 x-obs-oid（可能為空）。"""
    import http.client, ssl
    obs_params = base64.urlsafe_b64encode(
        json.dumps({"ver": "2.0", "name": filename, "type": "file"}).encode()
    ).rstrip(b'=').decode()

    parsed = urllib.parse.urlparse(_OBS_BASE + path)
    ctx = ssl.create_default_context()
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
            raise RuntimeError(f"OBS 上傳失敗 HTTP {resp.status}: {path}")
        return resp.getheader('x-obs-oid', '')
    finally:
        conn.close()


# ── 5. 上傳影片至 OBS ─────────────────────────────────────────────

def _obs_upload_video(obs_token: str, enc_video: bytes, filename: str,
                      enc_thumb: bytes | None) -> str:
    """
    POST 加密影片至 OBS /r/talk/emv/，回傳 OID。
    若有縮圖，以加密縮圖上傳至 {oid}__ud-preview（讓 mobile 顯示）。
    """
    reqid = f"reqid-{uuid.uuid4()}"
    oid = _obs_post(obs_token, enc_video, f"/r/talk/emv/{reqid}", filename)
    if not oid:
        raise RuntimeError("OBS 上傳回應沒有 x-obs-oid 標頭")

    # 上傳 preview（縮圖或影片本體）
    preview_data = enc_thumb if enc_thumb is not None else enc_video
    preview_name = Path(filename).stem + "_thumb.jpg" if enc_thumb else filename
    try:
        _obs_post(obs_token, preview_data, f"/r/talk/emv/{oid}__ud-preview",
                  preview_name)
        print("    preview 上傳完成", flush=True)
    except Exception as e:
        print(f"    preview 上傳失敗（忽略）: {e}", flush=True)

    return oid


# ── 6. 組 sendMessage body ────────────────────────────────────────

def _build_send_body(seq_num: int, to: str, my_mid: str,
                     oid: str, file_size: int, duration_ms: int,
                     chunks: list,
                     thumb_w: int = 0, thumb_h: int = 0) -> list:
    """組 sendMessage API body（contentType=2 影片）。"""
    content_meta = {
        "e2eeVersion": "2",
        "SID": "emv",
        "OID": oid,
        "FILE_SIZE": str(file_size),
        "DURATION": str(duration_ms),
    }
    if thumb_w and thumb_h:
        content_meta["MEDIA_THUMB_INFO"] = json.dumps(
            {"width": thumb_w, "height": thumb_h}
        )
    return [seq_num, {
        "from": my_mid, "to": to, "toType": 0,
        "id": f"local-{seq_num}", "contentType": _CT_VIDEO,
        "contentMetadata": content_meta,
        "hasContent": True,
        "chunks": chunks,
    }]


# ── 7. 完整流程 ───────────────────────────────────────────────────

async def send_video(page, to: str, file_path: Path) -> dict:
    """
    發送 E2EE V2 影片訊息。

    Args:
        page      - Playwright page（LINE extension）
        to        - 目標 mid
        file_path - 本機影片路徑（建議 mp4）

    Returns:
        {'ok': True, 'seq': <int>}  或  {'error': '...'}
    """
    video_data = file_path.read_bytes()
    file_size  = len(video_data)
    filename   = file_path.name

    print(">>> 讀取影片資訊...", flush=True)
    dur_ms, thumb_jpeg, thumb_w, thumb_h = _get_video_info(file_path)
    print(f"    時長: {dur_ms}ms, 縮圖: {'有' if thumb_jpeg else '無'} "
          f"({thumb_w}x{thumb_h})", flush=True)

    print(">>> 取得 token...", flush=True)
    token = await get_access_token(page)

    print(">>> 取得我的 key...", flush=True)
    my_mid, sender_key_id = await get_my_info(page)

    print(">>> 取得對方公鑰...", flush=True)
    receiver_key_id, receiver_pub_b64 = await get_recipient_key(page, token, to)

    print(">>> 生成 keyMaterial...", flush=True)
    km_b64, _ = _generate_km()

    print(">>> 加密影片...", flush=True)
    enc_video = _encrypt_data(video_data, km_b64)
    print(f"    明文 {file_size} bytes → 加密後 {len(enc_video)} bytes", flush=True)

    enc_thumb: bytes | None = None
    if thumb_jpeg:
        print(">>> 加密縮圖...", flush=True)
        enc_thumb = _encrypt_data(thumb_jpeg, km_b64)
        print(f"    縮圖 {len(thumb_jpeg)} bytes → 加密後 {len(enc_thumb)} bytes",
              flush=True)

    print(">>> 取得 OBS token...", flush=True)
    obs_token = await get_obs_token(page, token)

    print(">>> 上傳至 OBS...", flush=True)
    oid = _obs_upload_video(obs_token, enc_video, filename, enc_thumb)
    print(f"    OID={oid[:40]}...", flush=True)

    print(">>> E2EE 加密 keyMaterial...", flush=True)
    seq_num   = int(time.time() * 1000) & 0x7FFFFFFF
    plaintext = json.dumps({"keyMaterial": km_b64})
    chunks    = await encrypt_message(page, to, my_mid,
                                      sender_key_id, receiver_key_id,
                                      receiver_pub_b64, seq_num,
                                      plaintext, content_type=_CT_VIDEO)

    print(">>> 發送訊息...", flush=True)
    body_obj = _build_send_body(seq_num, to, my_mid, oid, file_size,
                                dur_ms, chunks, thumb_w, thumb_h)
    body_str = json.dumps(body_obj)
    hmac_val = await compute_hmac(page, token, _PATH_SEND, body_str)
    result   = call_api(_PATH_SEND, body_obj, token, hmac_val)

    if result.get('code') == 0:
        return {'ok': True, 'seq': seq_num}
    return {'error': f"sendMessage 失敗: {result}"}


# ── 8. 主程式 ─────────────────────────────────────────────────────

async def main():
    p = argparse.ArgumentParser(description="Send LINE video via GW API (E2EE V2)")
    p.add_argument("--to",   required=True, help="目標 mid")
    p.add_argument("--file", required=True, help="影片路徑（建議 mp4）")
    args = p.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"找不到檔案: {file_path}", file=sys.stderr)
        sys.exit(1)

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        result = await send_video(page, args.to, file_path)
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
