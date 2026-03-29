# AGENT_PLAN

- [ ] 2026-03-29 新增 global discipline：多步驟 pipeline 各步驟應獨立背景執行，各自有 PID、log 檔，可個別終止，不互相依賴同一 shell session。範本：`python step.py >> logs/step.log 2>&1 & echo "step PID: $!"`
