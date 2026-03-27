---
name: workstation-spec
description: "工作站規格評估：硬體規格、軟體架構、雲端方案評估框架，供採購決策使用。"
---

# Workstation Spec

從 `personal/build-work-station` 抽離的規格評估部分。

## 職責

提供工作站採購的評估框架：
- 硬體規格矩陣（CPU/GPU/RAM/Storage）
- 軟體架構選項（本地 vs 雲端 vs 混合）
- 預算估算模板

## 與其他組別的關係

```
intelligence/price-comparison  →  提供實際比價資料
infrastructure/workstation-spec →  評估規格與架構
operations/                    →  執行採購排程與預算審核
personal/build-work-station    →  前端展示與最終決策結果
```

## 狀態
⬜ 待建立（目前 personal/build-work-station 尚無規格評估文件，待補）
