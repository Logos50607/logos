---
name: terminal-to-workstation
trigger: manual
description: "從終端電腦將檔案或目錄傳輸至工作站，支援 rsync、scp 與壓縮傳輸。"
---

# Skill: terminal-to-workstation

## 用途

當需要將終端電腦（筆電/手機側）的檔案移至工作站（`/data/` 所在主機）時使用。

## 前置條件

- 工作站需開啟 SSH server（`systemctl status sshd`）
- 終端電腦與工作站在同一網路，或工作站有公開 IP/VPN

## 使用方式

### 1. 傳單一檔案

```bash
scp <本地路徑> logos@<workstation-ip>:<目標路徑>
# 範例
scp ~/Downloads/data.csv logos@192.168.1.100:/data/logos/intelligence/ai-chat-crawler/input/
```

### 2. 傳目錄（rsync，斷線續傳）

```bash
rsync -avz --progress <本地目錄>/ logos@<workstation-ip>:<目標目錄>/
# 範例
rsync -avz --progress ~/project/ logos@192.168.1.100:/data/personal/my-project/
```

### 3. 壓縮後傳輸（大量小檔案）

```bash
# 終端電腦
tar czf - <目錄> | ssh logos@<workstation-ip> "tar xzf - -C <目標父目錄>"
```

### 4. 反向：從工作站拉回終端

```bash
rsync -avz --progress logos@<workstation-ip>:<來源目錄>/ ~/local-backup/
```

## 工作站 IP 查詢

```bash
# 在工作站執行
ip addr show | grep "inet " | grep -v 127.0.0.1
```

## 注意事項

- 傳輸前確認目標路徑存在（`mkdir -p`）
- secrets / `.env` 傳輸後立即加入 `.gitignore`
- 大檔案建議用 rsync（斷線可續傳）
