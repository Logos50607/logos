---
name: cloud-monitor-gcp
description: "GCP billing 監控：Budget Alert → LINE 通知，BigQuery 費用查詢。"
---

# GCP Billing Monitor

## 現況（已完成）

| 項目 | 內容 |
|------|------|
| Billing account | `01E55D-F5B69B-F04706`（我的帳單帳戶） |
| BigQuery export | `trip-assistant-490916.billing_export`（2026-04-04 起） |
| Budget alert | 100 TWD，50%/90%/100% 門檻，email 通知 |
| Service Account | `billing-monitor@trip-assistant-490916.iam.gserviceaccount.com` |
| SA key | `~/.logos/secrets/gcp/billing-monitor-sa.json` |
| SA 權限 | `roles/billing.viewer`（billing account 層級） |

## Projects

| Project ID | 用途 | Billing | billable_to |
|------------|------|---------|-------------|
| `trip-assistant-490916` | Maps / Places / Cloud Run | 啟用 | self |
| `accounting-419607` | BigQuery / Compute | 啟用 | self |
| `tsldb-project` | BigQuery | 啟用 | self |
| `gen-lang-client-0013136576` | Gemini API | 未啟用 | - |
| `nodejs-cde2a` | Firebase | 未啟用 | - |

## 執行中的服務

| 服務 | Project | 規格 | 備註 |
|------|---------|------|------|
| Cloud Run: `thai-trip-2026` | `trip-assistant-490916` | 1 vCPU / 512Mi, min=0, max=20 | asia-east1 |

## 實作狀態

| 功能 | 狀態 | 備註 |
|------|------|------|
| LINE 通知串接（Budget Alert → Pub/Sub → CF） | 待實作 | LINE OA 尚未 ready |
| 每日費用摘要推播 | **程式完成**，等 OA ready 部署 | `cloud-function/` |
| 部署事件通知 | **程式完成**，等 OA ready 部署 | `cloud-function/` |
| 請款分流 | 藍圖 | - |

## 目錄結構

```
gcp/
  cloud-function/     # Cloud Functions 原始碼（兩個 entry point 共用）
    main.py           # daily_summary（HTTP）+ deploy_notify（Pub/Sub）
    billing.py        # BigQuery 費用查詢
    notifier.py       # LINE push（OA ready 前 stub 至 stdout）
    config.json       # project 清單與預算設定
    requirements.txt
  setup/
    01-pubsub.sh      # 建立 Pub/Sub topic + Log Sink（執行一次）
    02-scheduler.sh   # 建立 Cloud Scheduler job（需傳入 function URL）
    03-deploy.sh      # 部署兩個 Cloud Functions（Gen 2）
```

## 部署步驟（OA ready 後執行）

```sh
# 1. 建立 Pub/Sub topic 與 Log Sink（一次性）
cd gcp/setup && ./01-pubsub.sh

# 2. 部署 Cloud Functions（會印出 daily-summary URL）
./03-deploy.sh

# 3. 建立 Cloud Scheduler（傳入步驟 2 印出的 URL）
./02-scheduler.sh https://REGION-PROJECT.cloudfunctions.net/daily-summary

# 4. LINE OA ready 後，填入 token 重新部署
LINE_CHANNEL_ACCESS_TOKEN=xxx LINE_USER_ID=Uyyy ./03-deploy.sh
```

## LINE 通知格式

**每日費用摘要（每日 09:00）：**
```
[雲端費用摘要] 2026-04-04
本月累計（4月）：
  trip-assistant-490916: USD 1.4000 / 100 TWD (1%)
  accounting-419607:     USD 0.2000 / 200 TWD (0%)

燒錢速度：0.4000/天，月底預測 4.0000
```

**部署事件通知（即時）：**
```
[部署通知] 2026-04-04 17:23 UTC
動作：更新
服務：thai-trip-2026
專案：trip-assistant-490916
Image：asia-east1-docker.pkg.dev/.../thai-trip-2026:latest
部署者：yures611@gmail.com
```

---

## 待實作（藍圖）

### 1. LINE 通知串接（Budget Alert）
Budget Alert 目前只發 email，目標：
```
Budget Alert → Pub/Sub topic → Cloud Function → LINE push message
```

步驟：
1. 建立 Pub/Sub topic
2. 在 Budget 設定中加入 Pub/Sub 通知
3. 建立 Cloud Function 訂閱 topic，呼叫 LINE OA push API

### 2. 每日費用摘要
```
Cloud Scheduler（每日 09:00）→ Cloud Function
    → 查 BigQuery billing_export
    → 計算各 project 本月累計、燒錢速度、預測月底金額
    → LINE 推送摘要
```

BigQuery 查詢範例：
```sql
SELECT
  project.id,
  SUM(cost) AS total_cost,
  currency
FROM `trip-assistant-490916.billing_export.gcp_billing_export_v1_*`
WHERE DATE(_PARTITIONTIME) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY 1, 3
ORDER BY 2 DESC
```

### 3. 部署事件通知
每次 Cloud Run deploy 時推 LINE 通知：
```
Cloud Run deploy
    → Cloud Audit Log
    → Log Sink → Pub/Sub（同一個 topic）
    → Cloud Function → LINE 通知
```

通知格式：
```
[部署通知] 2026-04-04 17:23
服務：thai-trip-2026
專案：trip-assistant-490916
image：gcr.io/.../thai-trip-2026:latest
部署者：yures611@gmail.com
```

與 Budget Alert 共用同一個 Cloud Function，只是事件格式不同。

### 4. 請款分流
`billable_to != "self"` 的 project 產生獨立報告，方便向夥伴請款。

## 查費用（手動）

```
https://console.cloud.google.com/billing/01E55D-F5B69B-F04706/reports
```
