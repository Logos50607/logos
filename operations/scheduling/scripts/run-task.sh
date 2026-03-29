#!/bin/sh
# run-task.sh — 執行單一排程任務，產出執行報告
# Usage: run-task.sh <task_name> [trigger]

TASK="$1"
TRIGGER="${2:-scheduled}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCHEDULING_ROOT="$SCRIPT_DIR/.."
REGISTRY="$SCHEDULING_ROOT/registry"
MANIFEST="$REGISTRY/$TASK.md"

[ -z "$TASK" ] && echo "Usage: run-task.sh <task_name> [trigger]" && exit 1
[ ! -f "$MANIFEST" ] && echo "ERROR: manifest not found: $MANIFEST" && exit 1

# 從特定 section 提取欄位（處理縮排 YAML）
section_field() { python3 -c "
import re
c = open('$MANIFEST').read()
sec = re.search(r'^$1:\s*\n((?:[ \t]+\S.*\n?)*)', c, re.MULTILINE)
block = sec.group(1) if sec else c
m = re.search(r'^\s*$2:\s*[\"\']*([^\"\'\\n]+)[\"\']*', block, re.MULTILINE)
print(m.group(1).strip() if m else '')
" 2>/dev/null; }

field() { python3 -c "
import re
c = open('$MANIFEST').read()
m = re.search(r'^\s*$1:\s*[\"\']*([^\"\'\\n]+)[\"\']*', c, re.MULTILINE)
print(m.group(1).strip() if m else '')
" 2>/dev/null; }

CMD_TYPE=$(section_field "command" "type")
SCRIPT_PATH=$(section_field "command" "script_path")
PROMPT_PATH=$(section_field "command" "prompt_path")
WORKING_DIR=$(section_field "command" "working_dir")
MAX_ATTEMPTS=$(section_field "retry" "max_attempts"); MAX_ATTEMPTS="${MAX_ATTEMPTS:-1}"
DELAY=$(section_field "retry" "delay_seconds"); DELAY="${DELAY:-60}"

EXEC_ID="$(date +%Y%m%d-%H%M%S)-$TASK"
REPORT_DIR="$SCHEDULING_ROOT/reports/$(date +%Y%m%d)"
mkdir -p "$REPORT_DIR"
REPORT="$REPORT_DIR/$TASK.md"
DATA_TMP="/tmp/$EXEC_ID-data.txt"

START=$(date +%s)
attempt=1
status="failure"
output=""

run_once() {
    if [ "$CMD_TYPE" = "script" ]; then
        output=$(cd "$WORKING_DIR" && sh "$SCRIPT_PATH" 2>&1)
        [ $? -eq 0 ] && status="success" || status="failure"
    elif [ "$CMD_TYPE" = "ai-evaluate" ]; then
        [ -n "$SCRIPT_PATH" ] && (cd "$WORKING_DIR" && sh "$SCRIPT_PATH") > "$DATA_TMP" 2>&1
        prompt=$(cat "$WORKING_DIR/$PROMPT_PATH")
        [ -f "$DATA_TMP" ] && [ -s "$DATA_TMP" ] && prompt="$prompt

## 前置腳本輸出
$(cat "$DATA_TMP")"
        output=$(printf '%s' "$prompt" | claude -p 2>&1)
        [ -n "$output" ] && status="success" || status="failure"
    fi
}

while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
    run_once
    [ "$status" = "success" ] && break
    [ "$attempt" -lt "$MAX_ATTEMPTS" ] && sleep "$DELAY"
    attempt=$((attempt + 1))
done

END=$(date +%s)
DURATION=$((END - START))

cat > "$REPORT" << EOF
---
task_name: "$TASK"
execution_id: "$EXEC_ID"
timestamp: "$(date -Iseconds)"
status: "$status"
duration_seconds: $DURATION
attempt: $attempt
trigger: "$TRIGGER"
---

## 執行摘要

狀態：$status（嘗試 $attempt 次，耗時 ${DURATION}s）

## 輸出

\`\`\`
$output
\`\`\`
EOF

rm -f "$DATA_TMP"
echo "[$TASK] $status (${DURATION}s, attempt=$attempt) → $REPORT"
[ "$status" = "failure" ] && exit 1 || exit 0
