#!/bin/sh
# 驗證 apply-settings.sh：加入 baseline 鍵、保留既有鍵、冪等
DIR="$(cd "$(dirname "$0")" && pwd)"
T="$(mktemp -d)"; S="$T/settings.json"
echo "{\"hooks\":{\"Stop\":[]},\"tui\":\"fullscreen\"}" > "$S"
fail=0
chk() { [ "$2" = "$3" ] && echo "PASS  $1" || { echo "FAIL  $1: got $2"; fail=1; }; }

sh "$DIR/apply-settings.sh" "$S" >/dev/null
chk "cleanupPeriodDays" "$(jq .cleanupPeriodDays "$S")" 3650
chk "保留 tui"          "$(jq -r .tui "$S")" fullscreen
chk "保留 hooks"        "$(jq -c .hooks "$S")" "{\"Stop\":[]}"
first="$(cat "$S")"
sh "$DIR/apply-settings.sh" "$S" >/dev/null
chk "冪等"              "$(cat "$S")" "$first"
rm -rf "$T"; exit "$fail"
