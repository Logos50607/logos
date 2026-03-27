#!/bin/sh
# Strips remaining tags and cleans blank lines
# Usage: cat input | cleanup.sh
sed 's/<[^>]*>//g' | \
awk 'NF > 0 || last_empty == 0 { print; if (NF == 0) last_empty = 1; else last_empty = 0 }'
