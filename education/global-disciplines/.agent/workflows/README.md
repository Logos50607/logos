# Antigravity Workflows 系統

本目錄存放了 Antigravity 結構化的工作流 (Workflows)，主要透過 `/slash-commands`
指令觸發。

## 目錄結構

- `setup-project.md`: 初始化專案結構、Git 環境與管理清單。
- `fetch-web-content.md`: 擷取網頁內容並轉換為 Markdown 的標準流程。
- `commit.md`: 執行標準化的 Git 提交流程，包含變更分析與總結。

## 使用指引

1. **觸發方式**: 在對話中使用 `/指令名稱` 即可觸發。
2. **自動執行 (Turbo)**: 部分步驟若標註有 `// turbo` 註解，AI
   會在安全情況下自動執行相關指令。
3. **鏈接 (Chaining)**: 工作流之間可以互相調用以處理複雜的長流程任務。
