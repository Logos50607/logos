#!/bin/sh
# dispatch.sh — 每日排程入口：collect manifests → 篩選到期任務 → 執行 → 日報
# Usage: dispatch.sh [monorepo_root]

MONOREPO="${1:-/data/logos}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCHEDULING_ROOT="$SCRIPT_DIR/.."
REGISTRY="$SCHEDULING_ROOT/registry"
TODAY="$(date +%Y%m%d)"
REPORT_DIR="$SCHEDULING_ROOT/reports/$TODAY"
mkdir -p "$REPORT_DIR"

echo "=== daily-dispatch $(date -Iseconds) ==="

# 1. 更新 registry
sh "$SCRIPT_DIR/collect.sh" "$MONOREPO"

# 2. 讀取啟用任務清單
[ ! -f "$REGISTRY/index.md" ] && echo "ERROR: registry/index.md not found" && exit 1
tasks=$(grep '| true |' "$REGISTRY/index.md" | awk -F'|' '{print $2}' | tr -d ' ')

# 3. 篩選今日應執行的任務
due=""
for task in $tasks; do
    manifest="$REGISTRY/$task.md"
    [ ! -f "$manifest" ] && continue
    python3 "$SCRIPT_DIR/schedule-check.py" "$manifest" "$SCHEDULING_ROOT/reports" 2>/dev/null
    [ $? -eq 0 ] && due="$due $task" && echo "  due: $task"
done

[ -z "$due" ] && echo "  (no tasks due today)"

# 4. 執行到期任務
success=0; failure=0; skipped=0
for task in $due; do
    sh "$SCRIPT_DIR/run-task.sh" "$task" "scheduled"
    [ $? -eq 0 ] && success=$((success+1)) || failure=$((failure+1))
done

total=$((success + failure))

# 5. 產出日報
SUMMARY="$REPORT_DIR/daily-summary.md"
cat > "$SUMMARY" << EOF
---
date: "$(date +%Y-%m-%d)"
total_tasks: $total
success: $success
failure: $failure
partial: 0
skipped: $skipped
---

## 每日排程執行日報

| 任務 | 狀態 |
|------|------|
$(for task in $due; do
    rpt="$REPORT_DIR/$task.md"
    st=$(grep '^status:' "$rpt" 2>/dev/null | head -1 | sed 's/status: *"*//;s/"*//')
    echo "| $task | ${st:-unknown} |"
done)

EOF

echo "=== dispatch done: success=$success failure=$failure ==="
echo "日報：$SUMMARY"
