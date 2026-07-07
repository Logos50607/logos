#!/bin/sh
# stop-uncommitted-reminder.sh — Claude Code Stop hook
# 強制 git_usage §1 即時提交：回合結束時偵測未 commit 變更，提醒一次。
# stdin: hook JSON（含 .stop_hook_active 與 .cwd）
# 防迴圈：stop_hook_active 為 true 時直接放行（此 stop 已由本 hook 觸發過）。

INPUT=$(cat)

if command -v jq >/dev/null 2>&1; then
  ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
  DIR=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
else
  # 無 jq：保守解析。stop_hook_active 只要出現 true 即視為 true（防迴圈優先）
  case "$INPUT" in
    *'"stop_hook_active"'*true*) ACTIVE=true ;;
    *) ACTIVE=false ;;
  esac
  DIR=$(printf '%s' "$INPUT" | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
fi

# 防迴圈：本 hook 已 block 過一次，這次放行
[ "$ACTIVE" = "true" ] && exit 0

[ -n "$DIR" ] || DIR=$PWD

# 非 git repo → 放行
git -C "$DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

# 工作區乾淨 → 放行
STATUS=$(git -C "$DIR" status --porcelain 2>/dev/null)
[ -z "$STATUS" ] && exit 0

cat <<'EOF'
{"decision":"block","reason":"git_usage §1：偵測到未 commit 的變更。請執行 /git-commit，或若變更非本次所為／不宜提交，簡短說明後即可結束。"}
EOF
exit 0
