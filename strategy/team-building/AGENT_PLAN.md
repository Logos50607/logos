# TODOLIST

## 跨組基礎建設

- [ ] 2026-03-29 通訊組：起 `call-agent` 專案——封裝 `claude -p`，支援 caller 追溯（human / agent:<team> / cron:<job>）、目標組 disciplines + AGENT_PLAN 自動注入、可選額外 context 注入、call log 寫入；已有 global skill `claude-cli-subprocess` 作為技術基礎
- [ ] 2026-03-29 ~~聯絡組：規劃以 `claude -p` 做組間內部聯繫的核心機制~~ → 職責更正：agent 間通訊屬通訊組，聯絡組專責 agent ↔ 人類橋接

- [ ] 2026-03-28 教育組：建立「組織情境快照」定期產出機制——收集各組 git log、任務完成、重要決定，摘要成結構化 markdown，供各 bot / agent 啟動時注入為長期記憶（替代 hardcode 人設與知識）

- [ ] 2026-03-27 聯絡組：起「回報統整」專案，定義各組回報格式、收集方式、送達管道
- [ ] 2026-03-26 營運組排程 handle-failure 的 escalate 步驟：待聯絡組回報統整就位後啟用
- [ ] 2026-03-26 上述兩專案就位後，通知教育組 skill-adoption 可對接 maintain-vendor 的排程與回報
- [x] 2026-03-26 營運組：起「排程基礎建設」專案 → `/data/logos/operations/scheduling/`
      執行：建立 /data/logos/operations/scheduling/ 目錄與 README，定義 manifest 格式與排程基礎架構
      驗證：目錄存在，README 含 manifest 規格
      session: ~/.claude/projects/-data-logos-strategy-team-building/19921e77-ae14-419d-b91c-b880783f73b1.jsonl
- [ ] 2026-03-26 營運組排程：待教育組 maintain-vendor 作為首個 manifest 進行端到端驗證

## 外部技能吸納策略

- [ ] 2026-03-27 education/skill-adoption：將排程 adapter 與核心行為切開（核心可獨立呼叫，adapter 符合 scheduling manifest）
- [ ] 2026-03-26 待使用者核可策略框架後，由教育組依框架自行執行具體引入
- [x] 2026-03-26 擬定外部技能吸納策略框架 → `education/skill-adoption`
      執行：建立 education/skill-adoption 專案，定義外部技能評估、引入與維護的策略框架
      驗證：education/skill-adoption/ 存在，README 含策略框架說明
      session: ~/.claude/projects/-data-logos-strategy-team-building/781e07a1-e0e2-4aaa-b414-5266d6286176.jsonl

## Repo 建制

- [x] 2026-03-27 建立各組別 README.md（全部 11 組）
      執行：為 communication/creation/delivery/education/infrastructure/intelligence/internal-control/liaison/operations/strategy/supervision 各建立 README.md
      驗證：11 個組別目錄下均有 README.md
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl
- [x] 2026-03-27 switchboard 從 personal 移入 liaison/switchboard（git subtree，history 保留）
      執行：git subtree 將 personal/switchboard 搬至 liaison/switchboard，保留完整 git history
      驗證：liaison/switchboard/ 存在且 git log 含原始 commits
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl
- [x] 2026-03-27 補回 ~/.gemini symlink，修復 sync 機制
      執行：重建 ~/.gemini → global .agent/ 的 symlink
      驗證：sync_disciplines.sh 執行不報錯
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl
- [x] 2026-03-27 推送 monorepo 至 GitHub `Logos50607/logos`
      執行：git push origin master
      驗證：GitHub repo Logos50607/logos 可見最新 commits
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl
- [x] 2026-03-27 將 logos repo 重組為 monorepo
      執行：建立各組別頂層目錄結構，整合現有專案
      驗證：/data/logos/ 下有 11 個組別目錄
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl

## Personal Repo 拆解

- [ ] 2026-03-27 待使用者核可後：實際搬碼（thai-material / thai-trip / build-work-station / knowledge-base → 各組別）
- [ ] 2026-03-27 待使用者執行：刪除 GitHub dotfiles + digital-nomad；封存 TSL_project
- [x] 2026-03-27 建立拆解目標骨架（README）：creation/thai-slides、creation/thai-romanizer、intelligence/social-media-scraper、intelligence/price-comparison、intelligence/ai-chat-crawler、education/knowledge-synthesis、infrastructure/workstation-spec
      執行：為上述 7 個目標專案各建立目錄與 README.md（含核心目標、預期結構）
      驗證：7 個目錄存在，README 可讀
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl
- [x] 2026-03-27 分析 /data/personal/ 各 repo 並產出分類建議
      執行：讀取 personal/ 下各 repo，依職責對應至 11 組，產出分類表
      驗證：AGENT_PLAN.md 含分類結果與搬遷計畫
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl

## Global Disciplines

- [x] 2026-03-27 新增 modular_decomposition：拆解原則、薄消費者、delivery 設計、排程核心分離
      執行：建立 ~/.gemini/.agent/rules/modular_decomposition.md 並 sync
      驗證：~/.claude/.agent/rules/modular_decomposition.md 存在且內容正確
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl
- [x] 2026-03-27 新增 doc_before_impl：文件先於實作
      執行：建立 ~/.gemini/.agent/rules/doc_before_impl.md 並 sync
      驗證：~/.claude/.agent/rules/doc_before_impl.md 存在且內容正確
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl
- [x] 2026-03-27 新增 delivery/skills/consume-monorepo-module：通用 monorepo 模組消費 skill
      執行：建立 delivery/skills/consume-monorepo-module.md
      驗證：檔案存在且含使用方式說明
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl
- [x] 2026-03-27 新增 operations/skills/terminal-to-workstation：終端→工作站傳輸 skill
      執行：建立 operations/skills/terminal-to-workstation.md
      驗證：檔案存在且含傳輸指令說明
      session: ~/.claude/projects/-data-logos-strategy-team-building/f982686a-4614-423c-bf60-e893b916a598.jsonl
