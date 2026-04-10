# AGENT_PLAN — digest

- [x] 2026-04-10 設計資料庫 schema
      執行：建立 db/schema.sql，涵蓋 identity、event、task 三個語意層；更新 README
      驗證：schema.sql 含完整 DDL、views，README 已補資料庫設計說明

- [x] 2026-04-10 初始化 DB：建立 .env DB_URL 欄位、migrate 腳本，並在本機建立 digest DB
      執行：建立 db/setup.sh、更新 .env.example 加入 DB_URL；在 localhost:5433 建立 digest DB 並套用 schema
      驗證：psql \dt 確認 10 張表皆建立成功
- [ ] 2026-04-07 實作掃描器：依 .env 設定輪詢各 channel API，去重後寫入待分類佇列
- [ ] 2026-04-07 實作分類器：讀取 CLASSIFICATION_CONFIG 或使用內建預設，輸出分類結果
- [ ] 2026-04-07 實作呈報器：依 REPORT_SCHEDULE 定期組摘要並推送至 REPORT_CHANNEL
- [ ] 2026-04-07 串接排程：接入 operations/scheduling，使掃描與呈報可獨立排程
