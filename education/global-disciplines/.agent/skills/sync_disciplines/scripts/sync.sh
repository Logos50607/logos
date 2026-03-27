#!/bin/bash
# Description: Sync disciplines from global .agent source to agent-specific targets.
# Follows the Strategy Pattern implemented in shell functions.

CONFIG_FILE="/home/logos/.gemini/discipline_config.json"
AGENT_NAME="${1:-antigravity}"

# --- Checksum utilities ---
get_content_checksum() {
    echo -n "$1" | md5sum | cut -d' ' -f1
}

get_file_checksum() {
    if [[ ! -f "$1" ]]; then echo ""; return; fi
    md5sum "$1" | cut -d' ' -f1
}

# --- Strategies ---

# Strategy: soft_link
sync_soft_link() {
    local source="$1"
    local target="$2"
    echo "Processing soft_link: $source -> $target"
    
    mkdir -p "$(dirname "$target")"
    if [[ -L "$target" && "$(readlink -f "$target")" == "$(readlink -f "$source")" ]]; then
        echo "  Skipping: Link already exists and points to the same source."
        return
    fi
    
    ln -snf "$(realpath "$source")" "$target"
    echo "  Success: Linked $target to $source"
}

# Strategy: duplicate
sync_duplicate() {
    local source="$1"
    local target="$2"
    echo "Processing duplicate: $source -> $target"

    if [[ ! -f "$source" ]]; then
        echo "  Error: Source $source does not exist."
        return
    fi

    local src_sum=$(get_file_checksum "$source")
    local tgt_sum=$(get_file_checksum "$target")

    if [[ "$src_sum" == "$tgt_sum" ]]; then
        echo "  Skipping: File content matches."
        return
    fi

    mkdir -p "$(dirname "$target")"
    cp "$source" "$target"
    echo "  Success: Duplicated $source to $target"
}

# Strategy: insert_text
sync_insert_text() {
    local source_dir="$1"
    local target_file="$2"
    echo "Processing insert_text: $source_dir into $target_file"

    if [[ ! -d "$source_dir" ]]; then
        echo "  Error: Source directory $source_dir not found."
        return
    fi
    
    if [[ ! -f "$target_file" ]]; then
        mkdir -p "$(dirname "$target_file")"
        echo "# CLAUDE.md" > "$target_file"
        echo "  Created: $target_file"
    fi

    local start_marker="<!-- DISCIPLINE_START: $(basename "$source_dir") -->"
    local end_marker="<!-- DISCIPLINE_END: $(basename "$source_dir") -->"
    
    local combined_rules=""
    # Sort files to ensure stable order
    for f in $(ls "$source_dir"/*.md | sort); do
        local filename=$(basename "$f")
        local content=$(cat "$f")
        local checksum=$(get_content_checksum "$content")
        combined_rules+="\n<!-- START_FILE: $filename (MD5: $checksum) -->\n$content\n<!-- END_FILE: $filename -->\n"
    done

    local new_block=$(echo -e "${start_marker}${combined_rules}\n${end_marker}")
    
    local target_content=$(cat "$target_file")
    
    # Check if markers exist
    if grep -q "$start_marker" "$target_file"; then
        # Use python for stable multiline replacement as sed is painful with multiline variables
        python3 -c "
import sys, re
tc = sys.stdin.read()
nb = \"\"\"$new_block\"\"\"
pattern = re.escape(\"\"\"$start_marker\"\"\") + \".*?\" + re.escape(\"\"\"$end_marker\"\"\")
nr = re.sub(pattern, nb, tc, flags=re.DOTALL)
sys.stdout.write(nr)" <<< "$target_content" > "${target_file}.tmp"
    else
        echo -e "${target_content}\n\n${new_block}" > "${target_file}.tmp"
    fi

    if cmp -s "$target_file" "${target_file}.tmp"; then
        echo "  Skipping: Content already up to date."
        rm "${target_file}.tmp"
    else
        mv "${target_file}.tmp" "$target_file"
        echo "  Success: Updated content in $target_file"
    fi
}

# --- Main Runtime ---

# Parse JSON config using python snippet for reliability
items=$(python3 -c "
import json, sys
try:
    with open(\"$CONFIG_FILE\", 'r') as f:
        d = json.load(f)
    for agent in d:
        if agent['agent'] == \"$AGENT_NAME\":
            for disc in agent['disciplines']:
                print(f\"{disc['link_type']}|{disc['source']}|{disc['target']}\")
except Exception as e:
    sys.exit(1)
")

if [[ $? -ne 0 ]]; then
    echo "Failed to parse config or agent not found: $AGENT_NAME"
    exit 1
fi

while IFS="|" read -r link_type source target; do
    if [[ -n "$link_type" ]]; then
        "sync_$link_type" "$source" "$target"
    fi
done <<< "$items"
