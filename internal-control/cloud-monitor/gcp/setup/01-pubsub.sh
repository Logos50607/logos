#!/bin/sh
# 建立 Pub/Sub topic 與各 project 的 Cloud Run 部署事件 Log Sink
# 執行一次即可；重複執行會因資源已存在而報錯（可忽略）
set -e

TOPIC="cloud-run-deploy-events"
HOST_PROJECT="trip-assistant-490916"   # topic 建在這個 project
MONITOR_PROJECTS="trip-assistant-490916 accounting-419607 tsldb-project"
SINK_NAME="cloud-run-deploy-sink"
DEST="pubsub.googleapis.com/projects/${HOST_PROJECT}/topics/${TOPIC}"
FILTER='protoPayload.serviceName="run.googleapis.com" protoPayload.methodName=~"(CreateService|ReplaceService)"'

echo "=== 建立 Pub/Sub topic: ${TOPIC} ==="
gcloud pubsub topics create "${TOPIC}" --project="${HOST_PROJECT}"

for project in ${MONITOR_PROJECTS}; do
  echo "=== [${project}] 建立 Log Sink ==="
  gcloud logging sinks create "${SINK_NAME}" "${DEST}" \
    --project="${project}" \
    --log-filter="${FILTER}"

  # 取得 sink 的 writer identity 並授予 topic publisher 權限
  WRITER=$(gcloud logging sinks describe "${SINK_NAME}" \
    --project="${project}" \
    --format='value(writerIdentity)')
  echo "  writer identity: ${WRITER}"

  gcloud pubsub topics add-iam-policy-binding "${TOPIC}" \
    --project="${HOST_PROJECT}" \
    --member="${WRITER}" \
    --role="roles/pubsub.publisher"
done

echo "=== 完成 ==="
