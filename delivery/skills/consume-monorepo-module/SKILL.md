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

## 依賴記錄

引用任何 monorepo 模組時，必須在自己專案的 `DEPENDENCIES.md` 中記錄：

```markdown
| logos/<group>/<module> | - | <用途> | 路徑引用：`/data/logos/<group>/<module>/` |
```
