#!/bin/sh
# 監聽路由器重開後的網路恢復狀態
# 在本機（logos-as-a-philosopher）執行

TARGET="100.113.111.17"
echo "監聽 Proxmox（$TARGET）恢復中..."

i=0
while [ $i -lt 24 ]; do
  sleep 5
  result=$(tailscale ping --c 1 "$TARGET" 2>&1)
  echo "[$(date '+%H:%M:%S')] $result"
  if echo "$result" | grep -q "pong"; then
    echo "路由器已恢復！測試網路品質..."
    ssh -o ConnectTimeout=10 root@"$TARGET" "ping -c 3 8.8.8.8"
    break
  fi
  i=$((i+1))
done
