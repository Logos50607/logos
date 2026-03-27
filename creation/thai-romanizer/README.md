---
name: thai-romanizer
description: "泰語→羅馬拼音轉換器：tltk 斷詞 + IPA 轉換 + 改良 RTGS 聲調標記。"
---

# Thai Romanizer

從 `personal/thai-material` 抽離的泰語轉羅馬拼音模組。

## 來源
原始碼來自：`/data/personal/thai-material/.agent/skills/thai_processor/`

## 職責
- `romanize.py`：泰語字串 → 羅馬拼音（tltk 斷詞 + th2ipa + RTGS 轉換）
- `converters/rtgs_tonal.py`：IPA → 改良型 RTGS，含聲調記號

## 使用方式

```bash
uv run romanize.py "สวัสดี"
# 輸出: sa-wat-dii
```

## 狀態
⬜ 待從 personal/thai-material 正式遷入
