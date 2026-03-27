#!/bin/sh
# install.sh — Logos monorepo 環境初始化
# 冪等：重複執行安全
# 用法: sh install.sh

set -e
LOGOS_ROOT="$(cd "$(dirname "$0")" && pwd)"

# --- 載入 .env ---
ENV_FILE="$LOGOS_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo ">>> 找不到 .env，請先複製 .env.example 並填入本機路徑："
  echo "    cp $LOGOS_ROOT/.env.example $LOGOS_ROOT/.env"
  exit 1
fi
# shellcheck disable=SC1090
. "$ENV_FILE"

link() {
  src="$1"; dst="$2"
  if [ -L "$dst" ] && [ "$(readlink -f "$dst")" = "$(readlink -f "$src")" ]; then
    echo "  skip (已是正確 symlink): $dst"
  elif [ -e "$dst" ] && [ ! -L "$dst" ]; then
    echo "  backup: $dst -> $dst.bak"
    mv "$dst" "$dst.bak"
    ln -sf "$src" "$dst"
    echo "  linked: $dst -> $src"
  else
    ln -sf "$src" "$dst"
    echo "  linked: $dst -> $src"
  fi
}

echo ""
echo "=== 1. 建立 Secrets 目錄 ==="
mkdir -p "${SECRETS_DIR}/line-personal"
mkdir -p "${SECRETS_DIR}/line-official"
echo "  secrets dir: ${SECRETS_DIR}"

echo ""
echo "=== 2. 建立 Chrome Data 目錄 ==="
mkdir -p "${LINE_PERSONAL_CHROME_DATA}"
echo "  chrome data: ${LINE_PERSONAL_CHROME_DATA}"

echo ""
echo "=== 3. Symlinks ==="
# internal-control/secrets → $SECRETS_DIR
link "${SECRETS_DIR}" "$LOGOS_ROOT/internal-control/secrets"
# ~/.gemini → education/global-disciplines
link "$LOGOS_ROOT/education/global-disciplines" "${GEMINI_CONFIG_DIR}"

echo ""
echo "=== 4. Dotfiles ==="
sh "$LOGOS_ROOT/internal-control/dotfiles/install.sh"

echo ""
echo "=== 5. Sync Global Disciplines ==="
bash "${GEMINI_CONFIG_DIR}/.agent/skills/sync_disciplines/scripts/sync.sh" claude
bash "${GEMINI_CONFIG_DIR}/.agent/skills/sync_disciplines/scripts/sync.sh" antigravity

echo ""
echo "=== 完成 ==="
echo "下一步："
echo "  - 填入 ${SECRETS_DIR}/line-official/channel-secret"
echo "  - 填入 ${SECRETS_DIR}/line-official/channel-access-token"
echo "  - 啟動 Chrome（見 liaison/switchboard/src/channels/line/personal/README.md）"
