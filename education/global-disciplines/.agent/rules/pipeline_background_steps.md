---
name: pipeline_background_steps
trigger: always_on
description: "多步驟 pipeline 各步驟必須獨立背景執行，各有 PID 與 log 檔，可個別終止。"
---

# Pipeline 步驟獨立背景執行規範

## 核心規則

多步驟 pipeline（如 extract → lookup → abstract）的每個步驟，**必須作為獨立背景 process 執行**，不得串接在同一個 shell session 中依序阻塞執行。

## 執行範本

```bash
TS=$(date +%Y%m%d_%H%M%S)
python step_a.py >> logs/step_a_$TS.log 2>&1 &
echo "step_a PID: $!"

python step_b.py >> logs/step_b_$TS.log 2>&1 &
echo "step_b PID: $!"
```

## 為何這樣做

- 可個別 `kill <PID>` 終止單一步驟，不影響其他步驟
- 各步驟 log 獨立，方便除錯
- 步驟之間天然形成 pipeline：各步驟 poll 自己的 queue，資料從上游流向下游，不需要等前一步驟「全部完成」
- 一個步驟 crash 不會帶倒其他步驟

## 步驟設計原則

- 每個步驟都應實作 **while loop**：有資料就處理，無資料則退出
- 步驟之間透過資料庫的「待處理狀態」傳遞訊號（如 `place_id IS NULL`），不需要明確的 inter-process communication
- 這樣所有步驟可同時啟動，各自追著上游的進度跑
