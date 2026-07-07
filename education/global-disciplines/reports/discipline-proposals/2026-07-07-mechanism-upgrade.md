---
name: mechanism-upgrade
description: "制度機制升級決策紀錄：規則瘦身（trigger 分級載入）、hook 強制執行、決策分層。"
---

# 機制升級決策紀錄（2026-07-07）

session: /home/logos/.claude/projects/-home-logos-chat-with-agent/3d1b3686-a6e6-4f00-b69b-630d927e5251.jsonl

## 問題診斷（使用者核可的觀察）

1. **憲法厚、憲政機制薄**：26 條 always_on 規則全靠模型自律，規則越多單條遵守率越低；每個 session 為全部規則付 context 成本。
2. **使用者是單一審核點**：所有決策都回到使用者，瓶頸從「建制度」轉移到「審核」。

## 決策

### 1. 規則分級載入（立法：discipline_metadata §3）
- always_on 縮減至 12 條行為基線：agent_behavior、language、git_usage、decision-authority、ask-ruocosi、doc_before_impl、inventory_before_building、development_guidelines、secrets-management、project_setup_files、readme_management、workstation-environment
- 12 條改 model_decision（任務相關時按需讀取）：functional_core、dry_dynamic_keys、modular_decomposition、pipeline_background_steps、scraping_methodology、env-driven-config、port-registry、container-tooling、bootstrapping-direct-call、post-deploy-verify、skill-vs-tool
- agent_plan_update_triggers 改 glob（AGENT_PLAN.md）

### 2. sync 機制配合（實作：sync_disciplines）
insert_text 只全文注入 always_on；其餘規則生成「條件式規則索引」（name、觸發條件、description、路徑），agent 按需讀取。

### 3. Hook 強制執行（實作：dotfiles / ~/.claude）
- PreToolUse：攔截 agent 自行執行 sudo（強制 agent_behavior §4 提權邊界）
- Stop：回合結束偵測未 commit 變更，提醒一次（強制 git_usage 即時提交，防迴圈）

### 4. 決策分層（立法：decision-authority.md，新規則）
按錯誤回復成本分三層：agent 終審 / 批次呈報（帶預設值）/ 中斷等決。

## 待驗證

- sync 後 GEMINI.md 體積下降、索引正確
- hooks 需新 session 生效 → 待人工驗證
