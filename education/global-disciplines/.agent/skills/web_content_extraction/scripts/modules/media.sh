#!/bin/sh
# Convert <img> to Markdown
# Usage: cat input | media.sh
sed -E 's/<img[^>]*alt="([^"]*)"[^>]*src="([^"]*)"[^>]*>/![\1](\2)/g' | \
sed -E 's/<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>/![\2](\1)/g'
