#!/bin/sh
# start.sh - 啟動含 LINE extension 的 Chrome
#
# 功能:
#   1. 下載 LINE CRX（若 ext/ 目錄不存在）
#   2. 解壓 CRX 並注入正確 public key（確保 extension ID 與 Store 相同）
#   3. 取得 Chrome session 路徑
#   4. 啟動 Chrome，掛載 --load-extension
#   5. 等待 CDP 就緒
#
# 用法:
#   sh start.sh [--cdp-port 9222] [--display :99]
#
# 相依: curl, python3, Chrome（或 playwright install chromium）

set -e

# === 預設值 ===
CDP_PORT="${LINE_PERSONAL_CDP_PORT:-9222}"
DISPLAY_VAL="${LINE_PERSONAL_DISPLAY:-:99}"
LINE_EXT_ID_STORE="ophjlpahpchlmihnnnihgmmeilfjmjjc"
CRX_URL="https://clients2.google.com/service/update2/crx?response=redirect&prodversion=130.0&acceptformat=crx3&x=id%3D${LINE_EXT_ID_STORE}%26uc"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_DIR="$SCRIPT_DIR/ext"

# === 解析參數 ===
while [ $# -gt 0 ]; do
  case "$1" in
    --cdp-port) CDP_PORT="$2"; shift 2 ;;
    --display)  DISPLAY_VAL="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# === 取得 session 路徑 ===
if [ -n "$LINE_PERSONAL_SESSION" ]; then
  CHROME_DATA="$LINE_PERSONAL_SESSION"
elif [ -n "$LOGOS_ROOT" ]; then
  CHROME_DATA=$(bash "$LOGOS_ROOT/internal-control/scripts/get-secret.sh" \
    line-personal-session liaison/switchboard)
else
  echo "ERROR: 需設定 LINE_PERSONAL_SESSION 或 LOGOS_ROOT" >&2
  exit 1
fi

# === 取得 Chrome 路徑 ===
_find_chrome() {
  for c in google-chrome google-chrome-stable chromium chromium-browser \
            "$(ls ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome 2>/dev/null | tail -1)"; do
    [ -x "$c" ] 2>/dev/null && echo "$c" && return
    command -v "$c" > /dev/null 2>&1 && echo "$c" && return
  done
  echo "ERROR: 找不到 Chrome，請先執行: uv run --with playwright python3 -m playwright install chromium" >&2
  exit 1
}
CHROME_BIN=$(_find_chrome)

# === 下載、解壓、注入 key ===
if [ ! -d "$EXT_DIR" ]; then
  echo ">>> 下載 LINE extension..."
  TMP_CRX=$(mktemp /tmp/line_XXXXXX.crx)
  curl -sL -o "$TMP_CRX" "$CRX_URL"
  echo ">>> 解壓並注入 public key → $EXT_DIR"
  python3 - "$TMP_CRX" "$EXT_DIR" "$LINE_EXT_ID_STORE" <<'PYEOF'
import struct, zipfile, io, sys, json, hashlib, base64

def parse_varint(data, pos):
    result, shift = 0, 0
    while pos < len(data):
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80): break
        shift += 7
    return result, pos

def parse_bytes_field(data, pos):
    length, pos = parse_varint(data, pos)
    return data[pos:pos+length], pos+length

def scan_proto(data, depth=0):
    results = []
    pos = 0
    while pos < len(data):
        try:
            tag, pos = parse_varint(data, pos)
            wt = tag & 0x7
            if wt == 2:
                val, pos = parse_bytes_field(data, pos)
                results.append(val)
                if depth < 3: results.extend(scan_proto(val, depth+1))
            elif wt == 0: _, pos = parse_varint(data, pos)
            elif wt == 5: pos += 4
            elif wt == 1: pos += 8
            else: break
        except: break
    return results

def id_from_key(k):
    h = hashlib.sha256(k).hexdigest()[:32]
    return "".join(chr(ord('a') + int(c, 16)) for c in h)

crx_path, out_dir, target_id = sys.argv[1], sys.argv[2], sys.argv[3]
data = open(crx_path, 'rb').read()
assert data[:4] == b'Cr24', "Not CRX3"
header_len = struct.unpack_from('<I', data, 8)[0]
zip_data = data[12 + header_len:]
with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
    z.extractall(out_dir)

header_data = data[12:12 + header_len]
correct_key = next(
    (v for v in scan_proto(header_data) if 100 < len(v) < 600 and id_from_key(v) == target_id),
    None)
if correct_key:
    manifest_path = f"{out_dir}/manifest.json"
    m = json.loads(open(manifest_path).read())
    m["key"] = base64.b64encode(correct_key).decode()
    open(manifest_path, 'w').write(json.dumps(m, indent=2))
    print(f"  key 注入完成，extension ID: {target_id}")
else:
    print("  警告：找不到 public key，extension ID 可能不正確")
PYEOF
  rm -f "$TMP_CRX"
fi

# === 停止既有 Chrome CDP 實例 ===
pkill -f "chrome.*--remote-debugging-port=${CDP_PORT}" 2>/dev/null || true
sleep 1
rm -f "$CHROME_DATA/Default/LOCK" "$CHROME_DATA/Default/SingletonLock" \
      "$CHROME_DATA/SingletonLock" 2>/dev/null || true

# === 啟動 Chrome ===
echo ">>> 啟動 Chrome (CDP :${CDP_PORT})..."
DISPLAY="$DISPLAY_VAL" "$CHROME_BIN" \
  --remote-debugging-port="$CDP_PORT" \
  --user-data-dir="$CHROME_DATA" \
  --profile-directory="Default" \
  --load-extension="$EXT_DIR" \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-gpu \
  --no-first-run \
  >/tmp/chrome-line.log 2>&1 &

# === 等候 CDP 就緒 ===
echo ">>> 等候 CDP..."
for i in $(seq 1 15); do
  sleep 1
  curl -sf "http://localhost:${CDP_PORT}/json/version" > /dev/null 2>&1 && break
done

echo ">>> Chrome 已就緒，CDP: http://localhost:${CDP_PORT}"
echo ">>> 下一步: uv run login.py"
