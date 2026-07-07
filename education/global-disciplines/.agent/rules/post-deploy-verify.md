---
name: post_deploy_verify
trigger: model_decision
description: "部署完成後必須實際開啟產品（前端、API、CLI 等任何使用者觸達的入口）驗證可用，再宣告完成。Status 200 ≠ runtime OK。"
---

# 部署後驗證規範 (Post-Deploy Verification)

## 核心規則

**部署 / 發布完成後，必須實際操作該變更涉及的使用者入口，確認 runtime 行為正確，才能宣告任務完成。**

不得僅依賴：
- 部署腳本 stdout 的 200/201
- 編譯成功訊息
- 「上傳完成 ✅」
- pre-deploy smoke test

這些只證明「程式碼到達伺服器」，**不證明「使用者打開能看到正確結果」**。

## Why

歷次事故模式：

- 2026-04-23：ordering app VFS 部署成功（編譯 200、發布 200），但前端 runtime fetch 假日 API 在 `/ext/proxy` 拋 400。使用者打開頁面才看到爆炸。
- 2026-04-30：ordering app 銷貨單 + 最愛功能部署 200，前端載入後直接爆。客戶端打開才看到。

共同點：**部署狀態 200 與「使用者能用」之間有 runtime gap**（瀏覽器執行、權限、token、CSP、欄位 schema、JSON 解析等等），CI / 部署腳本看不到。

## How to apply

部署 / 發布完成後，依變更性質至少觸發其中一條：

| 變更類型 | 必驗動作 |
|---------|----------|
| 前端 VFS / TSX | 用實際使用者帳號開啟受影響頁面，確認載入無 console error、UI 正常顯示、互動可運作 |
| Server-side action | 用 `use_dev=true` 或直接 invoke action，看 200 + payload 結構正確（**不只看 status**） |
| DB schema / refs | 跑一次該表的 GET / POST 並讀取結果欄位 |
| Action with side effects（INSERT、扣庫存、寄信等） | 端到端跑一筆，再查結果記錄是否真的出現／狀態正確 |
| 部署腳本 / pipeline | 重跑 deploy，看新流程不破舊流程 |

若無法立即驗證（如需使用者手動登入），**必須在回報時明確標註「待人工驗證」，不得直接宣告完成**。

## 禁止行為

- 看到「發布: 200 / ✅」就宣告完成
- 把驗證責任丟給使用者（「請你開啟頁面確認」）卻同時宣告任務已完成
- 跳過驗證步驟，理由是「跟之前一樣的部署流程」、「上次能用這次應該也能」

## 例外

僅當下列同時成立才可省略部署後驗證：
1. 變更純粹是文件 / 註解 / 測試腳本，不影響 runtime
2. 已有自動化 smoke test 在 deploy pipeline 內執行並通過

否則，**必驗**。
