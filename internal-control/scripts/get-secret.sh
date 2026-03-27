#!/bin/sh
# get-secret.sh — 唯一合法的金鑰取用介面
# 用法: get-secret.sh <secret-name> <requester>
# 範例: get-secret.sh line-personal-session liaison/switchboard
#
# 輸出:
#   type=path → 輸出目錄絕對路徑至 stdout
#   type=file → 輸出檔案內容至 stdout
# 退出碼:
#   0 = 成功
#   1 = 用法錯誤
#   2 = 不在白名單
#   3 = secret 不存在

# --- 載入 .env ---
LOGOS_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$LOGOS_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  . "$ENV_FILE"
fi
SECRETS_DIR="${SECRETS_DIR:-$HOME/.logos/secrets}"
WHITELIST="$(dirname "$0")/../whitelist.json"
ACCESS_LOG="$(dirname "$0")/../registry/access.log"

SECRET_NAME="$1"
REQUESTER="$2"

# --- 用法檢查 ---
if [ -z "$SECRET_NAME" ] || [ -z "$REQUESTER" ]; then
  echo "用法: get-secret.sh <secret-name> <requester>" >&2
  exit 1
fi

# --- 白名單查詢 ---
result=$(python3 - "$SECRET_NAME" "$REQUESTER" "$WHITELIST" <<'EOF'
import json, sys

secret_name, requester, whitelist_path = sys.argv[1], sys.argv[2], sys.argv[3]

with open(whitelist_path) as f:
    whitelist = json.load(f)

for entry in whitelist:
    if entry["name"] == secret_name:
        if requester in entry["consumers"]:
            print(f"{entry['type']}:{entry['path']}")
            sys.exit(0)
        else:
            print(f"DENIED: {requester} 不在 {secret_name} 的白名單中", file=sys.stderr)
            sys.exit(2)

print(f"NOT_FOUND: secret '{secret_name}' 不存在於 whitelist", file=sys.stderr)
sys.exit(3)
EOF
)
exit_code=$?

if [ $exit_code -ne 0 ]; then
  exit $exit_code
fi

# --- 記錄存取 ---
mkdir -p "$(dirname "$ACCESS_LOG")"
printf "%s\t%s\t%s\n" "$(date -Iseconds)" "$REQUESTER" "$SECRET_NAME" >> "$ACCESS_LOG"

# --- 輸出 ---
secret_type="${result%%:*}"
secret_rel="${result#*:}"
secret_full="$SECRETS_DIR/$secret_rel"

if [ "$secret_type" = "path" ]; then
  if [ ! -d "$secret_full" ]; then
    echo "錯誤: 目錄不存在: $secret_full" >&2
    exit 3
  fi
  echo "$secret_full"
elif [ "$secret_type" = "file" ]; then
  if [ ! -f "$secret_full" ]; then
    echo "錯誤: 檔案不存在: $secret_full" >&2
    exit 3
  fi
  cat "$secret_full"
fi
