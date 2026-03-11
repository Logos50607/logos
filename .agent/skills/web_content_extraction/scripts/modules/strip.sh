#!/bin/sh
# Strip unnecessary HTML elements
sed -e '/<script/,/<\/script>/d' \
    -e '/<style/,/<\/style>/d' \
    -e '/<nav/,/<\/nav>/d' \
    -e '/<header/,/<\/header>/d' \
    -e '/<footer/,/<\/footer>/d' \
    -e '/<aside/,/<\/aside>/d'
