"""
extension.py - LINE Chrome extension 下載、解壓、key 注入與 ID 計算

對外介面:
  ensure_ready(ext_dir)  確認 ext/ 已解壓且 key 已注入，否則下載並處理
  get_id(ext_dir)        從 manifest.json key 計算 extension ID
"""

import base64, hashlib, io, json, struct, urllib.request, zipfile
from pathlib import Path

_STORE_ID      = "ophjlpahpchlmihnnnihgmmeilfjmjjc"
_PINNED_VERSION = "3.7.2"   # 逆向分析基準版本；升版前須重新驗證協議
_CRX_URL  = (
    "https://clients2.google.com/service/update2/crx"
    "?response=redirect&prodversion=130.0&acceptformat=crx3"
    f"&x=id%3D{_STORE_ID}%26uc"
)


def ensure_ready(ext_dir: Path) -> None:
    if ext_dir.exists() and (ext_dir / "manifest.json").exists():
        if _key_is_injected(ext_dir):
            return
    print(">>> 下載 LINE extension...")
    crx = urllib.request.urlopen(_CRX_URL).read()
    _unpack(crx, ext_dir)
    _inject_key(crx, ext_dir)
    _check_version(ext_dir)
    print(f">>> Extension 就緒，ID: {get_id(ext_dir)}")


def get_id(ext_dir: Path) -> str:
    manifest = json.loads((ext_dir / "manifest.json").read_text())
    key_b64 = manifest.get("key", "")
    if not key_b64:
        raise RuntimeError("manifest.json 缺少 key，請刪除 ext/ 重新執行")
    key_bytes = base64.b64decode(key_b64)
    return _id_from_key(key_bytes)


# ── 私有 ──────────────────────────────────────────────────────────

def _check_version(ext_dir: Path) -> None:
    """比對下載版本與逆向分析基準版本，不符時印警告。"""
    try:
        m = json.loads((ext_dir / "manifest.json").read_text())
        ver = m.get("version", "?")
        if ver != _PINNED_VERSION:
            print(f"⚠️  警告：下載版本 {ver} 與鎖定版本 {_PINNED_VERSION} 不符。")
            print("   媒體加密協議（chunked HMAC、ud-hash、SID mapping 等）可能已變動，")
            print("   請重新對 ext/static/js/main.js 驗證後再使用。")
        else:
            print(f">>> 版本確認：{ver}（符合鎖定版本）")
    except Exception:
        pass

def _id_from_key(key: bytes) -> str:
    h = hashlib.sha256(key).hexdigest()[:32]
    return "".join(chr(ord('a') + int(c, 16)) for c in h)


def _key_is_injected(ext_dir: Path) -> bool:
    try:
        m = json.loads((ext_dir / "manifest.json").read_text())
        return bool(m.get("key"))
    except Exception:
        return False


def _unpack(crx: bytes, ext_dir: Path) -> None:
    assert crx[:4] == b'Cr24', "不是 CRX3 格式"
    header_len = struct.unpack_from('<I', crx, 8)[0]
    zip_data = crx[12 + header_len:]
    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        z.extractall(ext_dir)


def _scan_proto(data: bytes, depth: int = 0) -> list[bytes]:
    """遞迴掃描 protobuf，回傳所有 bytes 型別的欄位值。"""
    results, pos = [], 0
    while pos < len(data):
        try:
            tag, pos = _varint(data, pos)
            wt = tag & 0x7
            if wt == 2:
                length, pos = _varint(data, pos)
                val = data[pos:pos + length]; pos += length
                results.append(val)
                if depth < 3:
                    results.extend(_scan_proto(val, depth + 1))
            elif wt == 0: _, pos = _varint(data, pos)
            elif wt == 5: pos += 4
            elif wt == 1: pos += 8
            else: break
        except Exception:
            break
    return results


def _varint(data: bytes, pos: int) -> tuple[int, int]:
    result, shift = 0, 0
    while pos < len(data):
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80): break
        shift += 7
    return result, pos


def _inject_key(crx: bytes, ext_dir: Path) -> None:
    header_len = struct.unpack_from('<I', crx, 8)[0]
    header = crx[12:12 + header_len]
    key = next(
        (v for v in _scan_proto(header)
         if 100 < len(v) < 600 and _id_from_key(v) == _STORE_ID),
        None)
    if not key:
        print("警告：找不到 public key，extension ID 可能不正確")
        return
    manifest_path = ext_dir / "manifest.json"
    m = json.loads(manifest_path.read_text())
    m["key"] = base64.b64encode(key).decode()
    manifest_path.write_text(json.dumps(m, indent=2))
