#!/bin/sh
# Convert inline styles (bold, italic, entities)
# Usage: cat input | inline.sh
sed -E 's/<strong[^>]*>/**/g; s/<\/strong>/**/g' | \
sed -E 's/<b[^>]*>/**/g; s/<\/b>/**/g' | \
sed -E 's/<em[^>]*>/*/g; s/<\/em>/*/g' | \
sed -E 's/<i[^>]*>/*/g; s/<\/i>/*/g' | \
sed 's/&nbsp;/ /g; s/&amp;/\&/g; s/&lt;/</g; s/&gt;/>/g; s/&quot;/"/g; s/&#39;/'\''/g'
