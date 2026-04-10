---
name: secrets-management
trigger: always_on
description: "Secret 集中管理規範：所有憑證一律存放於 /data/secrets/，透過 direnv .envrc 注入，並在 internal-control/whitelist.json 登記。"
---

# Secret 集中管理規範

## SSOT：/data/secrets/

所有 secret（API key、token、密碼、browser session、service account）的**唯一來源**是 `/data/secrets/`。
任何專案的 `.env`、程式碼或 discipline **不得存放 secret 值**。

## 目錄結構

```
/data/secrets/
├── <service>/          # 每個服務一個子目錄
│   └── <key-name>     # 每個值一個純文字檔（內容即值，無等號）
├── browser-sessions/   # Playwright / Chrome session JSON
├── gcp/                # GCP service account JSON
├── passwords/          # 非 API 類登入憑證
├── envs/               # （保留，已改用 direnv，通常為空）
└── backup.sh           # age 加密備份腳本
```

## 新增 Secret 的標準流程

新專案或新功能需要 secret 時，依序執行：

### 1. 建立 secret 檔案

```sh
mkdir -p /data/secrets/<service>
echo "# TODO: fill in" > /data/secrets/<service>/<key-name>
```

值填好後，檔案內容即為純值（不含 `KEY=` 前綴）。

### 2. 在 whitelist.json 登記

編輯 `/data/logos/internal-control/whitelist.json`，新增：

```json
{
  "name": "<service>-<key-name>",
  "description": "說明用途",
  "type": "file",
  "path": "<service>/<key-name>",
  "consumers": [
    "<group>/<project>"
  ]
}
```

path 類型：
- `"type": "file"` — 單一值檔案（`cat` 後即為值）
- `"type": "path"` — 目錄（如 browser session）

### 3. 在專案建立 .envrc

```sh
# /data/personal/<project>/.envrc
export MY_API_KEY=$(cat /data/secrets/<service>/<key-name>)
```

```sh
direnv allow .
```

`.envrc` **進版控**（它只描述「去哪拿什麼」，不含實際值）。

### 4. 不需要 .env.example

`.envrc` 本身即是文件（列出了所有需要的變數與來源路徑），不需要另建 `.env.example`。

## 取用方式

| 情境 | 方式 |
|------|------|
| 人類開發者（shell） | `cd` 進專案，direnv 自動注入 |
| AI agent / 腳本 | `get-secret.sh <name> <requester>`（需在 whitelist） |
| 程式碼 | `os.environ["MY_KEY"]` / `process.env.MY_KEY`（由 direnv 注入） |

## 備份

Secret 值變動後執行：

```sh
cd /data/secrets && ./backup.sh
```

輸出 `secrets.tar.age`（age passphrase 加密），手動上傳至雲端硬碟。

## 禁止行為

- 在 `.env`、程式碼、discipline 或任何進版控的檔案中寫入 secret 值
- 新增 secret 但不在 `whitelist.json` 登記
- 直接讀取 `/data/secrets/` 而不透過 `.envrc` 或 `get-secret.sh`（AI agent 適用）
