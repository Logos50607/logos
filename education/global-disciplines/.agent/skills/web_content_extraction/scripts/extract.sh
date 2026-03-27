#!/bin/sh
# ---------------------------------------------------------
# Antigravity HTML to Markdown Converter (Index Script)
# ---------------------------------------------------------
# Usage: ./extract.sh <URL|FILE|HTML> or cat file.html | ./extract.sh
# ---------------------------------------------------------
# 1. Input Handler: handle url/file/stdin
# 2. Processor Pipeline (Strategy Injection):
#    - strip.sh  : remove noise (style, script, nav)
#    - media.sh  : handle images (img)
#    - inline.sh : handle bold/italic/entities (strong, b, em, i)
#    - minor.sh  : remove spans/divs inside blocks
#    - links.sh  : handle <a> (must be after inner tags)
#    - blocks.sh : handle h1/p/li (structural)
#    - cleanup.sh: remove leftover tags & blank lines
# ---------------------------------------------------------

SOURCE=$1
MODULE_DIR="$(dirname "$0")/modules"
chmod +x "$MODULE_DIR"/*.sh 2>/dev/null

# Stage 1: Input Handling
if [ -n "$SOURCE" ]; then
    if [ -f "$SOURCE" ]; then
        CONTENT=$(cat "$SOURCE")
    elif echo "$SOURCE" | grep -qE '^https?://'; then
        USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        CONTENT=$(curl -sL -A "$USER_AGENT" "$SOURCE")
    else
        CONTENT="$SOURCE"
    fi
else
    CONTENT=$(cat)
fi

if [ -z "$CONTENT" ]; then
    echo "錯誤: 無法獲取內容。" >&2
    exit 1
fi

# Stage 2: Strategy Pipeline Injection
# Processing order is critical for handling nested HTML correctly.
echo "$CONTENT" | \
    "$MODULE_DIR/strip.sh" | \
    "$MODULE_DIR/media.sh" | \
    "$MODULE_DIR/inline.sh" | \
    "$MODULE_DIR/minor.sh" | \
    "$MODULE_DIR/links.sh" | \
    "$MODULE_DIR/blocks.sh" | \
    "$MODULE_DIR/cleanup.sh"
