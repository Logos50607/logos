#!/bin/sh
# test_pretooluse_deny_sudo.sh — pretooluse-deny-sudo.sh 的測試
# 驗證：sudo 指令被 deny、普通指令放行、字串內 sudo 不誤攔。

HOOK=$(dirname "$0")/pretooluse-deny-sudo.sh
PASS=0
FAIL=0

expect_deny() {
  desc=$1; payload=$2
  out=$(printf '%s' "$payload" | sh "$HOOK")
  if printf '%s' "$out" | grep -q '"permissionDecision":"deny"'; then
    echo "PASS (deny): $desc"; PASS=$((PASS+1))
  else
    echo "FAIL (expected deny): $desc"; echo "  output: $out"; FAIL=$((FAIL+1))
  fi
}

expect_allow() {
  desc=$1; payload=$2
  out=$(printf '%s' "$payload" | sh "$HOOK"); rc=$?
  if [ $rc -eq 0 ] && [ -z "$out" ]; then
    echo "PASS (allow): $desc"; PASS=$((PASS+1))
  else
    echo "FAIL (expected allow): $desc"; echo "  rc=$rc output: $out"; FAIL=$((FAIL+1))
  fi
}

# --- 應攔截 ---
expect_deny "行首 sudo" '{"tool_input":{"command":"sudo apt install foo"}}'
expect_deny "&& 之後" '{"tool_input":{"command":"ls -la && sudo systemctl restart nginx"}}'
expect_deny "; 之後" '{"tool_input":{"command":"cd /tmp; sudo rm -rf cache"}}'
expect_deny "|| 之後" '{"tool_input":{"command":"test -f x || sudo touch x"}}'
expect_deny "pipe 之後" '{"tool_input":{"command":"cat conf | sudo tee /etc/app.conf"}}'
expect_deny "\$( 之後" '{"tool_input":{"command":"echo $(sudo id -u)"}}'
expect_deny "換行後行首" '{"tool_input":{"command":"ls -la\nsudo reboot"}}'
expect_deny "行首 sudo 加空白" '{"tool_input":{"command":"  sudo whoami"}}'

# --- 應放行 ---
expect_allow "普通指令" '{"tool_input":{"command":"ls -la /tmp"}}'
expect_allow "雙引號字串內的 sudo" '{"tool_input":{"command":"echo \"sudo is not allowed\""}}'
expect_allow "grep 參數中的 sudo 詞" '{"tool_input":{"command":"grep sudoers /etc/group"}}'
expect_allow "visudo 非 sudo" '{"tool_input":{"command":"which visudo"}}'
expect_allow "無 command 欄位" '{"tool_input":{}}'

echo "----"
echo "PASS=$PASS FAIL=$FAIL"
[ $FAIL -eq 0 ] || exit 1
exit 0
