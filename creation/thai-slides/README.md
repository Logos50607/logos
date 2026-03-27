---
name: thai-slides
description: "泰語教材簡報生成器：HTML 設計稿 → PPTX，含絕對座標引擎與 HTML 預覽。"
---

# Thai Slides Generator

從 `personal/thai-material` 抽離的簡報生成模組，可獨立被任何需要 HTML→PPTX 轉換的專案呼叫。

## 來源
原始碼來自：`/data/personal/thai-material/.agent/skills/pptx_generator/` 與 `html_previewer/`

## 職責
- `convert_to_pptx.py`：HTML 設計稿 → PPTX（絕對座標引擎 V13，支援透明遮罩、漸層）
- `generate_preview.py`：Markdown + CSS → 預覽 HTML

## 使用方式

```bash
# 轉換 HTML → PPTX
uv run convert_to_pptx.py <input.html> <output.pptx>

# 生成預覽
uv run generate_preview.py <input.md> <output.html>
```

## 狀態
⬜ 待從 personal/thai-material 正式遷入
