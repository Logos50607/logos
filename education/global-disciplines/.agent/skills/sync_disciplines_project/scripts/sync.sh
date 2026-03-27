#!/bin/bash
# Description: Sync project-level .agent/ disciplines into .claude/ for Claude Code.
# Follows the same Strategy Pattern as the global sync_disciplines.sh.

PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CONFIG_FILE="$PROJECT_ROOT/.agent/discipline_config.json"
AGENT_NAME="claude"

# --- Checksum utilities ---
get_content_checksum() { echo -n "$1" | md5sum | cut -d' ' -f1; }
get_file_checksum() { [[ ! -f "$1" ]] && echo "" || md5sum "$1" | cut -d' ' -f1; }

# --- Strategies ---

sync_soft_link() {
    local source="$1" target="$2"
    echo "Processing soft_link: $source -> $target"
    mkdir -p "$(dirname "$target")"
    if [[ -L "$target" && "$(readlink -f "$target")" == "$(readlink -f "$source")" ]]; then
        echo "  Skipping: Link already exists and points to the same source."; return
    fi
    ln -snf "$(realpath "$source")" "$target"
    echo "  Success: Linked $target to $source"
}

sync_duplicate() {
    local source="$1" target="$2"
    echo "Processing duplicate: $source -> $target"
    [[ ! -f "$source" ]] && echo "  Error: Source $source does not exist." && return
    [[ "$(get_file_checksum "$source")" == "$(get_file_checksum "$target")" ]] \
        && echo "  Skipping: File content matches." && return
    mkdir -p "$(dirname "$target")"
    cp "$source" "$target"
    echo "  Success: Duplicated $source to $target"
}

sync_insert_text() {
    local source_dir="$1" target_file="$2"
    echo "Processing insert_text: $source_dir into $target_file"
    [[ ! -d "$source_dir" ]] && echo "  Error: Source directory $source_dir not found." && return
    if [[ ! -f "$target_file" ]]; then
        mkdir -p "$(dirname "$target_file")"
        echo "# CLAUDE.md" > "$target_file"
        echo "  Created: $target_file"
    fi

    local start_marker="<!-- DISCIPLINE_START: $(basename "$source_dir") -->"
    local end_marker="<!-- DISCIPLINE_END: $(basename "$source_dir") -->"
    local combined_rules=""
    for f in $(ls "$source_dir"/*.md 2>/dev/null | sort); do
        local content; content=$(cat "$f")
        local checksum; checksum=$(get_content_checksum "$content")
        combined_rules+="\n<!-- START_FILE: $(basename "$f") (MD5: $checksum) -->\n$content\n<!-- END_FILE: $(basename "$f") -->\n"
    done

    local new_block; new_block=$(echo -e "${start_marker}${combined_rules}\n${end_marker}")
    local target_content; target_content=$(cat "$target_file")

    if grep -q "$start_marker" "$target_file"; then
        python3 -c "
import sys, re
tc = sys.stdin.read()
nb = \"\"\"$new_block\"\"\"
nr = re.sub(re.escape(\"\"\"$start_marker\"\"\") + '.*?' + re.escape(\"\"\"$end_marker\"\"\"), nb, tc, flags=re.DOTALL)
sys.stdout.write(nr)" <<< "$target_content" > "${target_file}.tmp"
    else
        echo -e "${target_content}\n\n${new_block}" > "${target_file}.tmp"
    fi

    if cmp -s "$target_file" "${target_file}.tmp"; then
        echo "  Skipping: Content already up to date."; rm "${target_file}.tmp"
    else
        mv "${target_file}.tmp" "$target_file"
        echo "  Success: Updated content in $target_file"
    fi
}

# --- Main Runtime ---

if [[ -f "$CONFIG_FILE" ]]; then
    items=$(python3 -c "
import json, sys
with open('$CONFIG_FILE') as f: d = json.load(f)
for agent in d:
    if agent['agent'] == '$AGENT_NAME':
        for disc in agent['disciplines']:
            print(f\"{disc['link_type']}|{disc['source']}|{disc['target']}\")
" 2>/dev/null)
else
    # Default: sync rules -> CLAUDE.md, workflows -> commands/
    items="insert_text|$PROJECT_ROOT/.agent/rules|$PROJECT_ROOT/.claude/CLAUDE.md
soft_link|$PROJECT_ROOT/.agent/workflows|$PROJECT_ROOT/.claude/commands"
fi

while IFS="|" read -r link_type source target; do
    [[ -n "$link_type" ]] && "sync_$link_type" "$source" "$target"
done <<< "$items"
