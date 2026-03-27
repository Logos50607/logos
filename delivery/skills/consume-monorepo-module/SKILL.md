---
name: consume-monorepo-module
trigger: model_decision
description: "任何專案（含 personal）如何引用 monorepo 內的共享模組，以及何時應要求 delivery 組打包。"
---

# Skill: consume-monorepo-module

## 使用時機

當一個專案需要使用已抽離至 monorepo 的模組（`/data/logos/<group>/<module>/`）時。

## 引用方式

### 1. 路徑直接引用（工作站環境，優先）

直接用絕對路徑呼叫模組腳本，無需複製：

```bash
uv run /data/logos/<group>/<module>/scripts/<script>.py <args>
```

適用：本機工作站開發、CI/CD 在同一主機上執行。

### 2. 環境變數抽象化（推薦）

在專案 `.env` 中定義模組根路徑，避免硬編碼：

```bash
# .env
LOGOS_ROOT=/data/logos

# 呼叫時
uv run $LOGOS_ROOT/<group>/<module>/scripts/<script>.py <args>
```

### 3. 需要打包給外部時 → 交給 delivery 組

若需部署至無 monorepo 的環境或交付外部使用者，請提出以下需求給 delivery 組：

> 「需要打包 `<group>/<module>`，目標環境：<描述>，預期格式：[複製 / pip 套件 / Docker image]」

Delivery 組負責建立對應的 `build.sh` 或發布流程。

## Secrets 取用的雙模式

消費 monorepo 模組時，若模組需要金鑰，取用方式依部署環境不同：

| 環境 | 取用方式 |
|------|----------|
| 本地（monorepo） | `internal-control/scripts/get-secret.sh <name> <requester>` |
| 交付（standalone） | 直接讀 env var（不依賴 monorepo，無 get-secret.sh） |

### 消費端的正確寫法

消費端程式碼應實作一個薄的 secret resolver，優先讀 env var，fallback 至 get-secret.sh：

```sh
# 取得 secret 的統一方式
get_secret() {
  name="$1"
  env_var="$2"      # 交付模式的 env var 名稱（如 LINE_PERSONAL_SESSION）

  # 交付模式：env var 已設定，直接使用
  val=$(eval echo "\$$env_var")
  if [ -n "$val" ]; then
    echo "$val"
    return
  fi

  # 本地模式：透過 get-secret.sh
  bash "${LOGOS_ROOT}/internal-control/scripts/get-secret.sh" "$name" "$REQUESTER"
}
```

### 交付時的 .env.example

交付的 package 必須附上 `.env.example`，列出所有需要使用者填入的 secret env var：

```bash
# 範例
LINE_PERSONAL_SESSION=/path/to/chrome-session
LINE_OFFICIAL_CHANNEL_TOKEN=your-token-here
```

Delivery 組在打包時負責確認 `.env.example` 完整，且沒有任何 `get-secret.sh` 或 `LOGOS_ROOT` 的依賴殘留。

## 依賴記錄

引用任何 monorepo 模組時，必須在自己專案的 `DEPENDENCIES.md` 中記錄：

```markdown
| logos/<group>/<module> | - | <用途> | 路徑引用：`/data/logos/<group>/<module>/` |
```
