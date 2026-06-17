#!/bin/sh
# 透過 Telnet 重開 TP-Link MR600 路由器
# 在 logos-swift-sf314-59 上執行

ROUTER_IP=192.168.1.1
PASS_FILE=/tmp/rpass

if [ ! -f "$PASS_FILE" ]; then
  echo "錯誤：密碼檔案 $PASS_FILE 不存在"
  echo "請先在 swift 上執行：set +H && printf '%s' 'PASSWORD' > /tmp/rpass"
  exit 1
fi

PASSWORD=$(cat "$PASS_FILE")

echo "連接路由器 $ROUTER_IP ..."
(
  echo "$PASSWORD"
  sleep 1
  echo "dev reboot"
  sleep 3
) | telnet "$ROUTER_IP" 2>&1

echo "重開指令已送出，等待路由器重啟..."
