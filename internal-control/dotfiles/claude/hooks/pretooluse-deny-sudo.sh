#!/bin/sh
# pretooluse-deny-sudo.sh — Claude Code PreToolUse hook (matcher: Bash)
# 強制 agent_behavior §4 提權邊界：agent 不得自行執行 sudo。
# stdin: hook JSON（含 .tool_input.command）
# 攔截條件：sudo 以「指令位置」出現（行首、;、&、|、&& 、||、$(、` 之後）。
# 命中 → stdout 輸出 deny JSON；未命中 → exit 0 無輸出。

INPUT=$(cat)

# 取出待執行指令：優先 jq，無 jq 時以原始 JSON 保守比對（寧可誤攔，不可漏攔）
if command -v jq >/dev/null 2>&1; then
  CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
  # jq 解析失敗時退回原始輸入，避免漏攔
  [ -n "$CMD" ] || CMD=$INPUT
  SEP='(^|[;&|(]|\$\(|`)'
else
  # 無 jq：直接掃原始 JSON。JSON 中換行為 \n 字面值，故加入 \\n 作為分隔符
  CMD=$INPUT
  SEP='(^|[;&|(]|\$\(|`|\\n)'
fi

# sudo 出現在指令位置（分隔符後允許空白），且其後為空白或結尾
if printf '%s' "$CMD" | grep -Eq "${SEP}[[:space:]]*sudo([[:space:]]|\$)"; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"提權邊界（agent_behavior §4）：sudo 由使用者本人執行。請提供完整指令，請使用者以 ! <指令> 在對話中執行。"}}
EOF
  exit 0
fi

exit 0
