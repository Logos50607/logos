#!/bin/sh
# collect.sh — 掃描 monorepo 所有 *.manifest.md，更新 registry
# Usage: collect.sh [monorepo_root]

MONOREPO="${1:-/data/logos}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGISTRY="$SCRIPT_DIR/../registry"
mkdir -p "$REGISTRY"

# 從 frontmatter 提取欄位值
field() { python3 -c "
import re, sys
c = open(sys.argv[1]).read()
m = re.search(r'^$1:\s*[\"\']*([^\"\'\\n]+)[\"\']*', c, re.MULTILINE)
print(m.group(1).strip() if m else '')
" "$2" 2>/dev/null; }

tmp=$(mktemp)
find "$MONOREPO" -path "*/.agent/schedules/*.manifest.md" \
  ! -path "*/operations/scheduling/*" 2>/dev/null > "$tmp"

count=0
index=""

while IFS= read -r f; do
    task=$(field "task_name" "$f")
    [ -z "$task" ] && echo "  SKIP (no task_name): $f" && continue
    enabled=$(field "enabled" "$f")
    [ "$enabled" = "false" ] && en="false" || en="true"
    cp "$f" "$REGISTRY/$task.md"
    index="$index\n| $task | $en | $f |"
    echo "  registered: $task (enabled=$en)"
    count=$((count + 1))
done < "$tmp"
rm "$tmp"

printf '%s\n' "# Registry Index" "" \
  "自動產出，請勿手動編輯。更新：$(date -Iseconds)" "" \
  "| task_name | enabled | source |" "|-----------|---------|--------|" \
  > "$REGISTRY/index.md"
[ -n "$index" ] && printf "$index\n" >> "$REGISTRY/index.md"

echo "collect done: $count manifests"
