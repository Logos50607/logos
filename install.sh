#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GEMINI_LINK="$HOME/.gemini"

# 建立 ~/.gemini 軟連結指向本專案目錄
if [ -L "$GEMINI_LINK" ]; then
  echo "Symlink $GEMINI_LINK already exists -> $(readlink "$GEMINI_LINK")"
elif [ -e "$GEMINI_LINK" ]; then
  echo "Error: $GEMINI_LINK already exists and is not a symlink"
  exit 1
else
  ln -s "$SCRIPT_DIR" "$GEMINI_LINK"
  echo "Created symlink $GEMINI_LINK -> $SCRIPT_DIR"
fi
