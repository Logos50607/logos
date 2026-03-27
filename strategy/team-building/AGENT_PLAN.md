# TODOLIST

## 跨組基礎建設

- [ ] 2026-03-27 聯絡組：起「回報統整」專案，定義各組回報格式、收集方式、送達管道
- [ ] 2026-03-26 營運組排程 handle-failure 的 escalate 步驟：待聯絡組回報統整就位後啟用
- [ ] 2026-03-26 上述兩專案就位後，通知教育組 skill-adoption 可對接 maintain-vendor 的排程與回報
- [x] 2026-03-26 營運組：起「排程基礎建設」專案，定義註冊介面、頻率設定、失敗處理、執行結果格式 → 已交付至 `/data/logos/operations/scheduling/`
- [ ] 2026-03-26 營運組排程專案：待教育組 maintain-vendor 作為首個 manifest 進行端到端驗證

## 外部技能吸納策略

- [ ] 2026-03-26 待使用者核可策略框架後，由教育組依框架自行執行具體引入
- [x] 2026-03-26 擬定抽象的外部技能吸納策略框架，交付教育組 `skill-adoption` 專案

## Repo 建制

- [x] 2026-03-27 建立各組別的 README.md（全部 11 組）
- [x] 2026-03-26 將所有 GitHub repo 按組別分類，產出 REPO_CLASSIFICATION.md
- [x] 2026-03-27 將 logos repo 從 polyrepo 重組為 monorepo，所有組別統一於 `Logos50607/logos`
- [x] 2026-03-27 education/logos 改名為 education/global-disciplines，`.git` 提升至 `/data/logos/` repo root
- [x] 2026-03-27 移除子 repo 的 `.git`（team-building, scheduling, skill-adoption, dotfiles）併入 monorepo
- [x] 2026-03-27 清除舊 superpowers submodule 設定，改為直接納入
- [x] 2026-03-27 個人/待分類專案從 `_uncategorized/` 移至 `/data/personal/`
- [x] 2026-03-27 推送 monorepo 至 GitHub `Logos50607/logos`，history 完整保留
- [x] 2026-03-27 switchboard 從 personal 移入 liaison/switchboard（git subtree，history 保留）
- [x] 2026-03-27 補回 ~/.gemini symlink → /data/logos/education/global-disciplines，修復 sync 機制

## 待分類專案（/data/personal/）

已完成分析，待使用者核可後執行搬遷（見 ASK_HUMAN.md）：

- [x] 2026-03-27 分析並產出 /data/personal/ 各 repo 分類建議
- [ ] 2026-03-27 依核可結果執行 personal repo 搬遷（thai-material → creation、build-work-station → infrastructure、刪除重複 dotfiles）
