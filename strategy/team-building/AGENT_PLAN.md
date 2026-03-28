# TODOLIST

## 跨組基礎建設

- [ ] 2026-03-28 教育組：建立「組織情境快照」定期產出機制——收集各組 git log、任務完成、重要決定，摘要成結構化 markdown，供各 bot / agent 啟動時注入為長期記憶（替代 hardcode 人設與知識）

- [ ] 2026-03-27 聯絡組：起「回報統整」專案，定義各組回報格式、收集方式、送達管道
- [ ] 2026-03-26 營運組排程 handle-failure 的 escalate 步驟：待聯絡組回報統整就位後啟用
- [ ] 2026-03-26 上述兩專案就位後，通知教育組 skill-adoption 可對接 maintain-vendor 的排程與回報
- [x] 2026-03-26 營運組：起「排程基礎建設」專案 → `/data/logos/operations/scheduling/`
- [ ] 2026-03-26 營運組排程：待教育組 maintain-vendor 作為首個 manifest 進行端到端驗證

## 外部技能吸納策略

- [ ] 2026-03-27 education/skill-adoption：將排程 adapter 與核心行為切開（核心可獨立呼叫，adapter 符合 scheduling manifest）
- [ ] 2026-03-26 待使用者核可策略框架後，由教育組依框架自行執行具體引入
- [x] 2026-03-26 擬定外部技能吸納策略框架 → `education/skill-adoption`

## Repo 建制

- [x] 2026-03-27 建立各組別 README.md（全部 11 組）
- [x] 2026-03-27 switchboard 從 personal 移入 liaison/switchboard（git subtree，history 保留）
- [x] 2026-03-27 補回 ~/.gemini symlink，修復 sync 機制
- [x] 2026-03-27 推送 monorepo 至 GitHub `Logos50607/logos`
- [x] 2026-03-27 將 logos repo 重組為 monorepo

## Personal Repo 拆解

- [ ] 2026-03-27 待使用者核可後：實際搬碼（thai-material / thai-trip / build-work-station / knowledge-base → 各組別）
- [ ] 2026-03-27 待使用者執行：刪除 GitHub dotfiles + digital-nomad；封存 TSL_project
- [x] 2026-03-27 建立拆解目標骨架（README）：creation/thai-slides、creation/thai-romanizer、intelligence/social-media-scraper、intelligence/price-comparison、intelligence/ai-chat-crawler、education/knowledge-synthesis、infrastructure/workstation-spec
- [x] 2026-03-27 分析 /data/personal/ 各 repo 並產出分類建議

## Global Disciplines

- [x] 2026-03-27 新增 modular_decomposition：拆解原則、薄消費者、delivery 設計、排程核心分離
- [x] 2026-03-27 新增 doc_before_impl：文件先於實作
- [x] 2026-03-27 新增 delivery/skills/consume-monorepo-module：通用 monorepo 模組消費 skill
- [x] 2026-03-27 新增 operations/skills/terminal-to-workstation：終端→工作站傳輸 skill
