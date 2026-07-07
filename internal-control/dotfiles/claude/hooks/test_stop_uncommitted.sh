#!/bin/sh
# test_stop_uncommitted.sh — stop-uncommitted-reminder.sh 的測試
# 驗證：stop_hook_active=true 放行、dirty repo 觸發 block、乾淨/非 repo 放行。

HOOK=$(dirname "$0")/stop-uncommitted-reminder.sh
BASE=$(cd "$(dirname "$0")" && pwd)
PASS=0
FAIL=0

expect_block() {
  desc=$1; payload=$2
  out=$(printf '%s' "$payload" | sh "$HOOK")
  if printf '%s' "$out" | grep -q '"decision":"block"'; then
    echo "PASS (block): $desc"; PASS=$((PASS+1))
  else
    echo "FAIL (expected block): $desc"; echo "  output: $out"; FAIL=$((FAIL+1))
  fi
}

expect_pass() {
  desc=$1; payload=$2
  out=$(printf '%s' "$payload" | sh "$HOOK"); rc=$?
  if [ $rc -eq 0 ] && [ -z "$out" ]; then
    echo "PASS (allow): $desc"; PASS=$((PASS+1))
  else
    echo "FAIL (expected allow): $desc"; echo "  rc=$rc output: $out"; FAIL=$((FAIL+1))
  fi
}

# --- 測試環境 ---
# 必須建在系統 /tmp：若建在 $BASE 下，fixture 會位於 dotfiles 所屬 repo 內，
# 「非 git repo」案例將被外層 repo 誤判為 in-repo。
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

DIRTY="$TMP/dirty-repo"
mkdir -p "$DIRTY"
git -C "$DIRTY" init -q
echo "uncommitted" > "$DIRTY/file.txt"

CLEAN="$TMP/clean-repo"
mkdir -p "$CLEAN"
git -C "$CLEAN" init -q
echo "committed" > "$CLEAN/file.txt"
git -C "$CLEAN" add file.txt
git -C "$CLEAN" -c user.name=test -c user.email=test@test commit -qm init

NONREPO="$TMP/plain-dir"
mkdir -p "$NONREPO"

# --- 案例 ---
expect_pass  "stop_hook_active=true 防迴圈放行" "{\"stop_hook_active\":true,\"cwd\":\"$DIRTY\"}"
expect_block "dirty repo 觸發 block" "{\"stop_hook_active\":false,\"cwd\":\"$DIRTY\"}"
expect_pass  "乾淨 repo 放行" "{\"stop_hook_active\":false,\"cwd\":\"$CLEAN\"}"
expect_pass  "非 git repo 放行" "{\"stop_hook_active\":false,\"cwd\":\"$NONREPO\"}"

echo "----"
echo "PASS=$PASS FAIL=$FAIL"
[ $FAIL -eq 0 ] || exit 1
exit 0
