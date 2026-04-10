#!/bin/sh
# setup.sh - 初始化 digest PostgreSQL 資料庫
# 用法：sh db/setup.sh
# 需要 .env 已設定 DB_URL

set -e

SCRIPT_DIR=$(dirname "$0")
ROOT_DIR=$(dirname "$SCRIPT_DIR")

# 載入 .env
if [ -f "$ROOT_DIR/.env" ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "$ROOT_DIR/.env" | grep -v '^$' | xargs)
else
    echo "錯誤：找不到 .env，請先從 .env.example 複製並填入 DB_URL"
    exit 1
fi

if [ -z "$DB_URL" ]; then
    echo "錯誤：.env 中 DB_URL 為空"
    exit 1
fi

echo "套用 schema 至 $DB_URL ..."
psql "$DB_URL" -f "$SCRIPT_DIR/schema.sql"
echo "完成"
