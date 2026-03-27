# 排程基礎建設 (Scheduling Infrastructure)

## 核心目標

為 AI agent 團隊提供統一的排程任務註冊、執行、監管與回報機制。任何組別的任何專案，只要在自身目錄放置一份 manifest 檔案，即可將任務交由營運組按指定頻率執行。

## 設計理念

- **聲明式註冊**：各專案在自身 `.agent/schedules/` 放置 manifest，營運組掃描收集並執行，新增任務不需改動營運組程式碼。
- **Config-Driven**：所有排程參數（頻率、重試、告警）從 manifest 讀取，不硬編碼。
- **腳本/評估分層**：機械操作（script）與 AI 判斷（ai-evaluate）嚴格分開，不混淆。
- **標準化回報**：每次執行產出結構化報告，供監管與聯絡組回報使用。

## 對接介面

### 其他專案如何註冊排程

1. 複製 `templates/SCHEDULE_MANIFEST.md` 至專案的 `.agent/schedules/<task_name>.manifest.md`
2. 填寫 YAML frontmatter（task_name 格式：`<group>-<project>-<task>`）
3. 營運組的 `collect-manifests` workflow 每日自動掃描收集

### 營運組 → 聯絡組（回報統整）

- 輸入源：`reports/YYYYMMDD/daily-summary.md`
- 格式：見 `templates/EXECUTION_REPORT.md` 的日報格式區段
- 前置條件：待聯絡組「回報統整」專案就位

### 教育組 maintain-vendor 對接

- 教育組在 skill-adoption 專案放置 `ai-evaluate` 類型 manifest
- 前置條件：待本專案基礎定義完成

## 結構索引

```
scheduling/
├── .agent/
│   ├── rules/
│   │   ├── scheduling-principles.md      # 排程系統核心原則
│   │   └── execution-boundary.md         # 腳本層與評估層分界
│   ├── skills/
│   │   ├── schedule-health-check.md      # 排程健康檢查
│   │   └── execution-report-review.md    # 執行報告審閱
│   ├── workflows/
│   │   ├── collect-manifests.md          # 收集各專案 manifest
│   │   ├── run-scheduled-task.md         # 執行單一排程任務
│   │   ├── daily-dispatch.md             # 每日調度主流程
│   │   └── handle-failure.md             # 失敗處理流程
│   └── INDEX.md
├── templates/
│   ├── SCHEDULE_MANIFEST.md              # 排程註冊範本
│   └── EXECUTION_REPORT.md               # 執行結果報告範本
├── registry/                             # manifest 索引（自動維護）
├── reports/                              # 執行報告歸檔（自動產出）
├── README.md
├── AGENT_PLAN.md
└── ASK_HUMAN.md
```

## 實作原理

```
collect-manifests          daily-dispatch
      │                         │
      ▼                         ▼
掃描所有專案             讀取 registry/index.md
.agent/schedules/        比對 schedule 與今日日期
      │                         │
      ▼                         ▼
驗證 + 更新 registry     篩出待執行任務清單
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              run-scheduled-task (各任務獨立執行)
                    │
              ┌─────┴─────┐
              ▼           ▼
           script    ai-evaluate
              │           │
              ▼           ▼
         EXECUTION_REPORT (標準化報告)
              │
              ├──→ reports/YYYYMMDD/
              └──→ daily-summary.md → 聯絡組回報統整
```

## 專案狀態

- 初始化日期：2026-03-26
- 狀態：建制中
- 歸屬：營運組 (operations)
