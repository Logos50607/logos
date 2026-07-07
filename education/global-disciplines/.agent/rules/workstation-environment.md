---
name: workstation-environment
trigger: always_on
description: "工作站環境事實：VM 規格、連線方式、慣用工具與 monorepo 佈局。供所有 agent 建立環境假設，避免重複盤點或做出錯誤預設。"
---

# 工作站環境 (Workstation Environment)

本規則記載環境層級的事實。容器工具見 `container-tooling`，port 使用見 `port-registry`，secret 見 `secrets-management`。

## 主機與連線

- 工作站：Ubuntu 24.04 LTS VM（32G RAM），透過 **Tailscale** 連線；使用者本機為 Linux Mint。
- 使用者常在**手機與電腦間快速切換**操作同一個 session——不得假設對方在桌面環境，互動式步驟要能在手機上完成或改為背景執行。
- 遠端存取一律 SSH 優先（見 `prefer-ssh-over-gui-access`）。

## 慣用工具

- 終端環境：tmux；編輯器：neovim (LazyVim)；GitHub 操作：gh CLI。
- 產出檔案或指令時，以這些工具的慣例為預設（例如給 tmux 內可直接執行的指令，不假設 GUI 編輯器存在）。

## 版控與目錄佈局

- 組織 monorepo：`/data/logos/`，按組別分目錄（strategy、education、operations 等 11 組）。
- 版控策略：**polyrepo + meta repo 索引**——各專案獨立 repo，由 meta repo（logos）索引；不得把獨立專案硬併入單一 repo。
- 個人對話工作區：`~/chat-with-agent/`（DIARY.md、TODO_LIST.md）。
