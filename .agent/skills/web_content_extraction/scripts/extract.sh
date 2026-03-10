#!/bin/sh

# Antigravity Pure Shell HTML to Markdown Converter
# 支援從 URL 抓取、讀取檔案或從 STDIN 接收 HTML 內容

SOURCE=$1

# 如果有參數且不是從 STDIN 讀取
if [ -n "$SOURCE" ]; then
    if [ -f "$SOURCE" ]; then
        # 如果是檔案
        CONTENT=$(cat "$SOURCE")
    elif echo "$SOURCE" | grep -qE '^https?://'; then
        # 如果是 URL
        USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        CONTENT=$(curl -sL -A "$USER_AGENT" "$SOURCE")
    else
        # 否則視為直接讀取內容 (可能是傳入 HTML 字串，但建議用 pipe)
        CONTENT="$SOURCE"
    fi
else
    # 從 STDIN 讀取
    CONTENT=$(cat)
fi

if [ -z "$CONTENT" ]; then
    echo "錯誤: 無法獲取內容。使用方式: $0 <URL|FILE|HTML> 或 cat file.html | $0" >&2
    exit 1
fi

# 核心轉換邏輯
echo "$CONTENT" | \
    # 移除 script, style 區塊及其內容
    sed -e '/<script/,/<\/script>/d' -e '/<style/,/<\/style>/d' | \
    # 移除 nav, header, footer, aside
    sed -e '/<nav/,/<\/nav>/d' -e '/<header/,/<\/header>/d' -e '/<footer/,/<\/footer>/d' -e '/<aside/,/<\/aside>/d' | \
    # 處理標題 h1-h6
    sed -E 's/<h1[^>]*>/\n\n# /g; s/<\/h1>/\n/g' | \
    sed -E 's/<h2[^>]*>/\n\n## /g; s/<\/h2>/\n/g' | \
    sed -E 's/<h3[^>]*>/\n\n### /g; s/<\/h3>/\n/g' | \
    sed -E 's/<h4[^>]*>/\n\n#### /g; s/<\/h4>/\n/g' | \
    sed -E 's/<h5[^>]*>/\n\n##### /g; s/<\/h5>/\n/g' | \
    sed -E 's/<h6[^>]*>/\n\n###### /g; s/<\/h6>/\n/g' | \
    # 處理段落與換行
    sed -E 's/<p[^>]*>/\n\n/g; s/<\/p>/\n/g' | \
    sed -E 's/<br[^>]*>/\n/g' | \
    # 處理列表
    sed -E 's/<li[^>]*>/ - /g; s/<\/li>/\n/g' | \
    # 處理加粗與斜體
    sed -E 's/<strong[^>]*>/**/g; s/<\/strong>/**/g' | \
    sed -E 's/<b[^>]*>/**/g; s/<\/b>/**/g' | \
    sed -E 's/<em[^>]*>/*/g; s/<\/em>/*/g' | \
    sed -E 's/<i[^>]*>/*/g; s/<\/i>/*/g' | \
    # 處理超連結 <a>
    sed -E 's/<a[^>]*href="([^"]*)"[^>]*>([^<]*)<\/a>/[\2](\1)/g' | \
    # 處理圖片 <img>
    sed -E 's/<img[^>]*alt="([^"]*)"[^>]*src="([^"]*)"[^>]*>/![\1](\2)/g' | \
    # 處理實體符號
    sed 's/&nbsp;/ /g; s/&amp;/\&/g; s/&lt;/</g; s/&gt;/>/g; s/&quot;/"/g; s/&#39;/'\''/g' | \
    # 移除所有其餘的 HTML 標籤
    sed 's/<[^>]*>//g' | \
    # 清理多餘的空白行 (使用 awk)
    awk 'NF > 0 || last_empty == 0 { print; if (NF == 0) last_empty = 1; else last_empty = 0 }'
