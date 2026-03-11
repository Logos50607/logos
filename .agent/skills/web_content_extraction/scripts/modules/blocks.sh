#!/bin/sh
# Convert block level tags (h1-h6, p, li, br)
# Usage: cat input | blocks.sh
sed -E 's/<h1[^>]*>/\n\n# /g; s/<\/h1>/\n/g' | \
sed -E 's/<h2[^>]*>/\n\n## /g; s/<\/h2>/\n/g' | \
sed -E 's/<h3[^>]*>/\n\n### /g; s/<\/h3>/\n/g' | \
sed -E 's/<h4[^>]*>/\n\n#### /g; s/<\/h4>/\n/g' | \
sed -E 's/<h5[^>]*>/\n\n##### /g; s/<\/h5>/\n/g' | \
sed -E 's/<h6[^>]*>/\n\n###### /g; s/<\/h6>/\n/g' | \
sed -E 's/<p[^>]*>/\n\n/g; s/<\/p>/\n/g' | \
sed -E 's/<li[^>]*>/ - /g; s/<\/li>/\n/g' | \
sed -E 's/<br[^>]*>/\n/g'
