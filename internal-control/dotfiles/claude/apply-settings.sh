#!/bin/sh
# 把 settings-baseline.json 的鍵合併進 ~/.claude/settings.json（baseline 優先，其餘保留）
# 冪等：重複執行結果相同。用法：sh apply-settings.sh [settings.json 路徑]

DIR="$(cd "$(dirname "$0")" && pwd)"
BASE="$DIR/settings-baseline.json"
TARGET="${1:-$HOME/.claude/settings.json}"

command -v jq >/dev/null 2>&1 || { echo "需要 jq" >&2; exit 1; }
mkdir -p "$(dirname "$TARGET")"
[ -s "$TARGET" ] || echo "{}" > "$TARGET"

tmp="$(mktemp)" || exit 1
if jq -s ".[0] * .[1]" "$TARGET" "$BASE" > "$tmp"; then
  cp "$TARGET" "$TARGET.bak"
  mv "$tmp" "$TARGET"
  echo "applied: $BASE -> $TARGET"
else
  rm -f "$tmp"
  echo "合併失敗，未修改 $TARGET" >&2
  exit 1
fi
