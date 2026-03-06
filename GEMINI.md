# Antigravity Global Rules

## Workspace Initialization Rule

Whenever a new folder or workspace is opened with Antigravity:

1. **Always** ensure there is a .agent directory at the root of the workspace.
2. **Required Subdirectories**: Within the .agent directory, consistently create
   both .rules and .skills subdirectories if they do not already exist.
3. **Proactive Check**: Upon starting a conversation in any workspace, verify
   the presence of these directories and create them immediately if they are
   missing.
4. **TODO List**:
   在工作區根目錄應始終存在`TODOLIST.md`。如果不存在，應主動建議建立或直接建立。此文件**僅用於紀錄使用者
   (USER)
   需處理的事項**：包含尚未裁斷的衝突、尚未完成的開發項目、或未來需注意/完善的部分。AI
   正在進行的工作應記錄在 Commit 訊息中，而非此文件。
   - **格式規範**: 必須以條列式撰寫，每項前需有 Checkbox (如 \`- [
     ]\`)，並在標號後加上日期 (如 \`2026-03-06\`)。
   - **排序規範**: 新加入（日期較晚）的項目應放置在文件的最上方。

## Proactive Rule and Skill Maintenance

- **Continuous Learning**: During discussions, if you identify project-specific
  conventions, repeating patterns, or specialized tasks that should be
  regularized, proactively formalize them.
- **Immediate Action**: Create or update the relevant files in the local
  .agent/rules or .agent/skills directory as soon as the need is identified,
  without waiting for explicit user instructions to "save" the rule.
- **Consistency**: Ensure that all new rules and skills follow the standard
  format for the workspace.

## Git 提交規範

- **自動提交**：只要對開發或內容檔案進行修改，在完成一個邏輯單位的變更後，必須主動執行
  Git commit。
- **提交前置作業**：在執行 commit 之前，必須先執行 `git diff`
  (或查看目前的變更內容)，從中歸納出本次修改的實質要旨。
- **訊息格式**：Commit
  訊息應包含從變更內容歸納出的要旨，簡明地說明修改內容，並統一使用正體中文撰寫。

## 行為規範 (Behavioral Rules)

- **重複指令限制**：當你已經重複類似指令 3
  次以上（如連續失敗的嘗試或無進展的循環操作），必須主動中斷目前流程並切換做法（例如：重新分析問題、採用不同工具或向使用者尋求進一步說明）。
