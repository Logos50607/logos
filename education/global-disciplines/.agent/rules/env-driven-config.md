---
name: env-driven-config
trigger: always_on
description: "非 secret 的外部設定參照模式：路徑、端點、feature flag 等一律以 .env 宣告，不得 hardcode。Secret 值另見 secrets-management 規範。"
---

# 外部設定參照規範 (Env-Driven External Config)

## 適用範圍

**本規範適用於非 secret 的可變設定**，例如：
- 指向其他服務的 API 端點（如 `http://localhost:8000`）
- 指向外部資料目錄的本地路徑（如 `/data/personal/line-personal/data`）
- 可因部署環境不同而改變的 flag 或參數

**Secret 值（API key、token、密碼）不適用本規範，改見 `secrets-management` 規則。**

## 核心規則

**任何可因環境而異的非 secret 設定，一律寫入 `.env`，不得 hardcode 於程式碼或 discipline 中。**

## 必備檔案

每個使用 `.env` 的專案或模組，必須同時提供：

| 檔案 | 說明 |
|------|------|
| `.env` | 實際值，**gitignored**，不進版控 |
| `.env.example` | 範本，進版控，列出所有欄位、預設值與用途說明 |
| `.gitignore` | 明確列出 `.env`（不依賴 global gitignore） |

若專案同時有 secret（`.envrc`）和非 secret 設定（`.env`），兩者並存：
- `.envrc`：讀 `/data/secrets/`，進版控
- `.env`：非 secret 的環境設定，gitignored

## .env.example 格式要求

每個欄位必須包含：
1. 一行**中文說明**（`#` 開頭）說明用途
2. 欄位名稱與示例值（或留空並說明何時填入）

```bash
# LINE 個人帳號 FastAPI 端點（留空則跳過此 channel）
LINE_PERSONAL_API=http://localhost:8000

# 分類規則設定檔絕對路徑（留空使用內建預設）
CLASSIFICATION_CONFIG=
```

## Symlink vs .env 路徑的選擇

| 情境 | 建議 |
|------|------|
| 需要讓工具或腳本直接存取目錄（如 `ls`、`cat`） | 建 symlink，路徑寫進 `.env` 說明其指向 |
| 只需透過 API 或程式碼讀取 | 只寫 `.env` 路徑，不建 symlink |
| symlink 目標位置會因環境不同 | 用 `.env` 指定路徑，腳本在 setup 時建 symlink |

若使用 symlink，setup 腳本（如 `setup.sh`）須從 `.env` 讀取目標路徑並建立連結，**不得硬編碼 symlink 目標**。

## 禁止行為

- 在 Python/Shell/JS 程式碼中直接寫死路徑或端點
- 在 `.md` discipline 中寫入任何環境特定路徑
- 把 `.env`（含實際值）commit 進 git
- 在 `.env` 或 `.env.example` 中放入 secret 值（→ 改用 `secrets-management` 流程）
