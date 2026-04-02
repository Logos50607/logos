#!/bin/bash
# ensure-services.sh - 確保 LINE personal 背景服務持續執行
#
# 服務：
#   sync.py          - 訊息同步 daemon（每 5-600s 輪詢）
#   media_server.py  - 媒體 HTTP server（port 8889）
#
# 設計：冪等，已在執行則跳過；不在執行才啟動

set -euo pipefail

PERSONAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="$PERSONAL_DIR/logs"
mkdir -p "$LOGS"

ts() { date "+%H:%M:%S"; }

_ensure() {
    local name="$1" script="$2"
    if pgrep -f "$script" > /dev/null 2>&1; then
        echo "[$(ts)] $name 已在執行（PID: $(pgrep -f "$script" | head -1)）"
        return
    fi
    echo "[$(ts)] $name 未執行，啟動中..."
    cd "$PERSONAL_DIR"
    nohup uv run "$script" >> "$LOGS/${name}.log" 2>&1 &
    echo "[$(ts)] $name 啟動 PID: $!"
}

_ensure "sync"         "sync.py"
_ensure "media-server" "webapp/media_server.py"
