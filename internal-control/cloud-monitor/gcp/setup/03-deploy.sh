#!/bin/sh
# 部署兩個 Cloud Functions（Gen 2）
# 執行前確認已設定好 LINE 環境變數，或保持空白用 stub
set -e

PROJECT="trip-assistant-490916"
REGION="asia-east1"
SA="billing-monitor@${PROJECT}.iam.gserviceaccount.com"
SOURCE="$(cd "$(dirname "$0")/../cloud-function" && pwd)"
TOPIC="cloud-run-deploy-events"

# LINE 環境變數（OA ready 後填入；留空則 stub 至 log）
LINE_TOKEN="${LINE_CHANNEL_ACCESS_TOKEN:-}"
LINE_USER="${LINE_USER_ID:-}"

COMMON_FLAGS="--gen2
  --project=${PROJECT}
  --region=${REGION}
  --runtime=python311
  --source=${SOURCE}
  --service-account=${SA}
  --memory=256Mi
  --timeout=60s
  --set-env-vars=LINE_CHANNEL_ACCESS_TOKEN=${LINE_TOKEN},LINE_USER_ID=${LINE_USER}"

echo "=== 部署 daily-summary (HTTP trigger) ==="
# shellcheck disable=SC2086
gcloud functions deploy daily-summary \
  ${COMMON_FLAGS} \
  --entry-point=daily_summary \
  --trigger-http \
  --no-allow-unauthenticated

echo ""
echo "=== 部署 deploy-notify (Pub/Sub trigger) ==="
# shellcheck disable=SC2086
gcloud functions deploy deploy-notify \
  ${COMMON_FLAGS} \
  --entry-point=deploy_notify \
  --trigger-topic="${TOPIC}"

echo ""
echo "=== 完成 ==="
FUNC_URL=$(gcloud functions describe daily-summary \
  --gen2 --project="${PROJECT}" --region="${REGION}" \
  --format='value(serviceConfig.uri)')
echo "daily-summary URL: ${FUNC_URL}"
echo "請將此 URL 傳給 02-scheduler.sh"
