#!/bin/sh
# Convert <a> to Markdown
# Usage: cat input | links.sh
# Because inner tags have been converted to markdown (which doesn't contain '<'), 
# [^<]* can match the content between tags reliably.
sed -E 's/<a[^>]*href="([^"]*)"[^>]*>([^<]*)<\/a>/[\2](\1)/g'
