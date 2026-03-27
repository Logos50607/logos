#!/bin/sh
# Strip minor grouping tags like <span> or generic tags that shouldn't affect link extraction
# But keep the content.
sed -E 's/<\/?(span|div|section|article)[^>]*>//g'
