# AGENT_PLAN — digest

- [ ] 2026-04-07 實作掃描器：依 .env 設定輪詢各 channel API，去重後寫入待分類佇列
- [ ] 2026-04-07 實作分類器：讀取 CLASSIFICATION_CONFIG 或使用內建預設，輸出分類結果
- [ ] 2026-04-07 實作呈報器：依 REPORT_SCHEDULE 定期組摘要並推送至 REPORT_CHANNEL
- [ ] 2026-04-07 串接排程：接入 operations/scheduling，使掃描與呈報可獨立排程
