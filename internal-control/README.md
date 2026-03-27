---
name: internal-control
description: "內控組：env、secrets、dotfiles、metadata 管理。"
---

# 內控組 (Internal Control)

## 核心目標

管理工作站的底層設定與機密：dotfiles、環境變數、secrets 與系統 metadata，確保環境可重現、機密不外洩。

## 專案

| 專案 | 說明 |
|------|------|
| `dotfiles/` | tmux、git、bash、nvim 等設定檔，透過 `install.sh` symlink 至家目錄 |

## 安裝

```bash
bash /data/logos/internal-control/dotfiles/install.sh
```

## 設計原則

- 家目錄的設定檔一律為 symlink，指向本 repo 為 SSOT
- secrets 不進版控（`.gitignore` 排除）
