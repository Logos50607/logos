# AGENT_PLAN

- [ ] 2026-04-04 LINE OA 搬遷：將 `src/channels/line/official/` 核心邏輯移至 `/data/personal/line-official/`，switchboard 保留薄 adapter
- [ ] 2026-04-04 LINE personal channel adapter 改寫：`src/channels/line/personal/` 改為呼叫 `line-personal` FastAPI :8000，移除舊版 CDP 程式碼
- [ ] 2026-03-23 完成專案初始化（目錄結構、.agent 同步）
- [ ] 2026-03-23 釐清各 channel 的 API 限制（LINE/Discord/Trello 未讀保護機制）
- [ ] 2026-03-23 設計核心資料模型（Message → Task）
- [ ] 2026-03-23 建立 channels 介接層骨架
- [ ] 2026-03-23 建立 processors 訊息分析模組
- [ ] 2026-03-23 建立 output 任務清單產生模組
