---
name: claude-cli-subprocess
description: "用 claude -p 在腳本中呼叫 Claude 做內容理解、摘要、抽取。適用於需要 LLM 推理但無法互動的自動化流程。"
---

# 技能：用 claude CLI 做子流程推理

## 核心用法

```bash
echo "<內容>" | claude -p "<指令>"
# 或
cat file.json | claude -p "<指令>"
# 或在 Python 中
subprocess.run(["claude", "-p", PROMPT], input=content, capture_output=True, text=True)
```

`-p` (print mode)：非互動執行，stdin 為輸入，stdout 為輸出，適合嵌入自動化流程。

## 典型應用場景

- **地點抽取**：從爬蟲 transcript/text 抽取結構化地點清單
- **摘要生成**：批次摘要文章或影片逐字稿
- **分類標記**：對大量內容做 label/tag
- **資料清洗**：結構不一致的 JSON 轉標準格式

## 設計原則

1. **prompt 要求只輸出 JSON**，不要說明文字，方便 parse
2. **輸入截斷**：只傳必要欄位（title + text[:1000] + transcript[:1500]），避免超出 context
3. **錯誤處理**：用 `start = output.find("[")` 找 JSON 邊界，容錯非預期輸出
4. **timeout**：建議 60 秒，長文可放寬至 120 秒

## Python 範本

```python
import json, subprocess, sys
from pathlib import Path

PROMPT = """請從以下內容抽取地點，只回傳 JSON array：
[{"name": "...", "type": "餐廳/廟宇/景點", "notes": "一句話摘要"}]
若無地點，回傳 []。"""

def call_claude(payload: dict) -> list:
    result = subprocess.run(
        ["claude", "-p", PROMPT],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, timeout=60,
        cwd=Path(__file__).parents[2],  # 專案根目錄（讓 claude 讀到正確 context）
    )
    output = result.stdout.strip()
    start, end = output.find("["), output.rfind("]") + 1
    if start == -1 or end == 0:
        return []
    return json.loads(output[start:end])
```

## 注意事項

- `cwd` 設為專案根目錄，讓 claude 讀到 CLAUDE.md 等 context
- 若在 CI / headless 環境執行，確認 `claude` CLI 已安裝且有 API key
- 輸出品質依賴 prompt 品質，複雜任務可用多輪（先抽取，再驗證）
