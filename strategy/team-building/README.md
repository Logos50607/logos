# Team Building — 組別建制專案

## 核心目標 (Core Goal)

規劃並建制所有 agent 團隊的組別架構，確保各組職責明確、模組化且可相互引用，避免重工。

## 背景

本專案源自工作站搬遷過程中，對 agent 團隊架構的討論與規劃。所有組別統一收納於 `Logos50607/logos` monorepo（`/data/logos/`），個人/待分類專案獨立於 `/data/personal/`。

## 組別架構

| 組別 | 英文代號 | 職責 |
|------|----------|------|
| 策略組 | strategy | 專案規劃、決策、優先級 |
| 資訊蒐集組 | intelligence | 爬蟲、外部資料取得 |
| 教育組 | education | 規範制定、技能培訓、互動觀察與總結、教育人類 |
| 聯絡組 | liaison | 對人類的資訊傳達與提醒 |
| 營運組 | operations | 定期執行的固定任務 |
| 監督組 | supervision | Code review、QA、測試 |
| 創作組 | creation | 腳本/圖片/聲音等模型生成任務 |
| 內控組 | internal-control | env、secrets、dotfiles、metadata |
| 基礎建設組 | infrastructure | VM、容器、CI/CD、資料庫、網路 |
| 通訊組 | communication | Agent 間通訊模組 |
| 交付組 | delivery | 模組打包、建置、發布 |

## 結構索引 (Structure Index)

```
team-building/
├── .agent/             # 專案規範
│   ├── rules/
│   ├── skills/
│   └── workflows/
├── README.md           # 本文件
├── AGENT_PLAN.md       # AI 計畫執行事項
├── ASK_HUMAN.md        # 需請示使用者的項目
└── REPO_CLASSIFICATION.md  # GitHub repo 分組對照表
```

## 設計原則

- **Monorepo**：所有組別收納於 `logos` repo，以目錄區分組別與專案
- **模組化**：所有專案盡量切割成模組後相互引用，避免重工
- **SSOT**：每項資源只有一個權威來源，其餘以引用方式取用

## 專案初始化紀錄

- 初始化日期：2026-03-26
- 狀態：建制中
