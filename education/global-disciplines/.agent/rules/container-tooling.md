---
name: container-tooling
trigger: model_decision
description: "容器工具規範：logos 環境一律使用 podman，禁止使用 docker CLI 或 docker-compose。"
---

# 容器工具規範 (Container Tooling)

## 核心規則

**logos 環境使用 rootless podman，不是 docker。**

- `docker` CLI 無法存取（無 socket 權限）
- `docker-compose` / `podman-compose` CLI 不存在
- 一律使用 `podman` 直接操作容器

## 常用指令對照

| 操作 | 指令 |
|------|------|
| 查看容器狀態 | `podman ps` |
| 重啟容器 | `podman restart <container>` |
| 查看 log | `podman logs -f <container>` |
| 進入容器 | `podman exec -it <container> bash` |
| 執行一次性指令 | `podman exec <container> <cmd>` |

## source code live-mount

各專案若在 `docker-compose.yml` 中 live-mount source code，改完後 **`podman restart` 即生效，不需要重 build image**。
