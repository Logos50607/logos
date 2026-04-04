#!/bin/sh
# 建立 Cloud Scheduler job，每日 09:00 (Asia/Taipei) 觸發 daily-summary
# 用法：./02-scheduler.sh <daily-summary-function-url>
set -e

PROJECT="trip-assistant-490916"
REGION="asia-east1"
FUNCTION_URL="${1:?請傳入 daily-summary function URL，例如: ./02-scheduler.sh https://...}"

echo "=== 建立 Cloud Scheduler job ==="
gcloud scheduler jobs create http daily-billing-summary \
  --project="${PROJECT}" \
  --location="${REGION}" \
  --schedule="0 9 * * *" \
  --uri="${FUNCTION_URL}" \
  --http-method=GET \
  --time-zone="Asia/Taipei" \
  --description="每日費用摘要推播" \
  --oidc-service-account-email="billing-monitor@${PROJECT}.iam.gserviceaccount.com"

echo "=== 完成 ==="
echo "手動觸發測試：gcloud scheduler jobs run daily-billing-summary --project=${PROJECT} --location=${REGION}"
