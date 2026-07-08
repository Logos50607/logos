# TODOLIST

- [x] 2026-07-07 制度機制升級：trigger 分級載入、決策分層、hooks 強制執行
      執行：discipline_metadata 新增 §3 載入策略；12 條規則改 model_decision、1 條改 glob、
      新增 decision-authority 規則；sync_insert_text 依 trigger 分流並生成條件式規則索引；
      Claude Code hooks（sudo 攔截、未 commit 提醒）進 dotfiles/claude/ 並註冊 settings.json；
      救回孤兒規則 consume_external_projects、清除 GEMINI.md marker 外殘留
      驗證：test_sync.sh 5 案例、hooks 測試 17 案例全數通過；GEMINI.md 1502 → 566 行；
      hooks 已於 2026-07-08 以新 headless session 端到端實測生效
      （sudo 呼叫被 PreToolUse deny、dirty repo 收尾被 Stop block 一次後正常結束）
      決策紀錄：reports/discipline-proposals/2026-07-07-mechanism-upgrade.md
      session: /home/logos/.claude/projects/-home-logos-chat-with-agent/3d1b3686-a6e6-4f00-b69b-630d927e5251.jsonl
- [ ] 2026-07-07 觀察分級載入成效：若某條 model_decision 規則常被漏讀，升回 always_on 或改為 hook
      （session: /home/logos/.claude/projects/-home-logos-chat-with-agent/3d1b3686-a6e6-4f00-b69b-630d927e5251.jsonl）
- [ ] 2026-03-20 整合 `/setup-project` 與 `/sync-disciplines`： - 移除專案中的
      `GEMINI.md`，將初始化資訊改寫入 `README.md`。 - 在 `/setup-project`
      的最後一步自動執行同步機制。
- [x] 2026-03-10 實作 `/fetch-web-content` 工作流與高品質網頁擷取工具
      `extract.sh`
- [x] 2026-03-10 建立開發規範 Rules (`development_guidelines.md`) 與依賴管理
      (`DEPENDENCIES.md`)
- [x] 2026-03-10 整理 Antigravity Rules、Workflows 與 Skills 官方文件內容並加入
      skills 目錄
- [x] 2026-03-11 增加腳本 100 行限制與索引化/注入設計（Pipe/Strategy）開發規範

- [x] 2026-03-14 清理 Git 歷史紀錄，將 `projects.json`, `settings.json`,
      `trustedFolders.json` 加入 `.gitignore` 並從所有歷史中移除。
- [x] 2026-03-09 區分 TODOLIST 與 ASKHUMAN 管理
- [x] 2026-03-09 整理 GEMINI.md 並完成語言規則設定
