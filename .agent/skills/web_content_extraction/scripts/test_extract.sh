#!/bin/sh

# Test Script for extract.sh
SCRIPT="./.agent/skills/web_content_extraction/scripts/extract.sh"

# 確保腳本存在且可執行
chmod +x "$SCRIPT"

echo "=== 開始測試 extract.sh ==="

# 測試 1: 處理標題與段落
echo "測試 1: 標題與段落"
echo "<h1>Title</h1><p>Hello world.</p>" | "$SCRIPT" | grep -q "# Title" && echo "[OK] 標題轉換成功" || echo "[FAIL] 標題轉換失敗"

# 測試 2: 處理超連結
echo "測試 2: 超連結"
echo '<a href="https://example.com">Example</a>' | "$SCRIPT" | grep -q "\[Example\](https://example.com)" && echo "[OK] 超連結轉換成功" || echo "[FAIL] 超連結轉換失敗"

# 測試 3: 處理實體符號與加粗
echo "測試 3: 實體符號與加粗"
echo "<strong>&amp; Check</strong>" | "$SCRIPT" | grep -q "\*\*& Check\*\*" && echo "[OK] 實體符號與加粗成功" || echo "[FAIL] 實體符號與加粗失敗"

# 測試 4: 排除 script 與 style
echo "測試 4: 排除無效標籤"
RESULT=$(echo "<style>body{color:red}</style><p>Content</p><script>alert(1)</script>" | "$SCRIPT")
if echo "$RESULT" | grep -qvE "body|alert"; then
    echo "[OK] 成功排除 script 與 style 內容"
else
    echo "[FAIL] 腳本或樣式內容殘留"
fi

echo "=== 測試完成 ==="
