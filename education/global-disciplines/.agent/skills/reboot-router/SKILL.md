---
name: reboot-router
description: 重開台灣家用 TP-Link Archer MR600 4G 路由器。當 Tailscale 連線到台灣機器延遲異常（ SSH 卡頓時使用。透過 logos-swift-sf314-59 跳板機以 Telnet 連入路由器執行重開機指令。
trigger: manual
---

# 重開 TP-Link MR600 路由器

## 背景

台灣那端的網路走 4G（TP-Link Archer MR600），連線不穩時需要重開路由器讓它重新接上基站。
無法直接從外部存取路由器，需透過同一 LAN 上的 logos-swift-sf314-59（100.101.218.2）跳板。

## 診斷：什麼時候需要重開？

1. 從本機 ping Proxmox 延遲 > 500ms 或封包遺失
2. SSH 到 logos-proxmox-host 或 logos-ubuntu-dev 卡頓或 timeout
3. 在 Proxmox / ubuntu-dev 上 ping 8.8.8.8 延遲 > 300ms 或封包遺失 > 10%

## 執行流程

### Step 1：確認問題在路由器

```bash
tailscale ping --c 3 100.113.111.17
ssh root@100.113.111.17 ping -c 3 8.8.8.8
```

若 Tailscale 能 ping 通但 8.8.8.8 延遲很高，就是 4G 連線問題，執行重開。

### Step 2：透過 swift 跳板重開路由器

密碼存放於 swift 的 `/tmp/rpass`（若不存在，請使用者先建立）：

```bash
ssh logos@100.101.218.2 sh /home/logos/.gemini/.agent/skills/reboot-router/scripts/reboot.sh
```

### Step 3：監聽恢復

```bash
sh ~/.gemini/.agent/skills/reboot-router/scripts/monitor.sh
```

## 重要資訊

| 項目 | 值 |
|------|-----|
| 路由器 | TP-Link Archer MR600（4G） |
| 路由器 LAN IP | 192.168.1.1 |
| 跳板機 | logos-swift-sf314-59（100.101.218.2） |
| 跳板機帳號 | logos |
| 登入方式 | Telnet（port 23），只需密碼，不需帳號 |
| 重開指令 | `dev reboot` |
| 密碼位置 | swift 上的 `/tmp/rpass`（臨時，每次需重建） |
| 恢復時間 | 約 60 秒 |

## 注意事項

- 重開後 Tailscale 會自動重連，不需手動操作
- SSH 登入路由器失敗（legacy key 問題），只能用 Telnet
- Web UI 登入 API 目前無法使用（71234 錯誤，原因不明）
