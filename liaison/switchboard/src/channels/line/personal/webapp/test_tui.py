"""
test_tui.py - tui.py 輔助函式單元測試

測試範圍（不需要 LINE / CDP）：
  - _ts()         timestamp 格式化
  - _meta()       contentMetadata 解析
  - _preview()    訊息預覽文字
  - _save/_load   messages.json 讀寫
  - ChatItem      label / preview / unread 屬性
  - ContactPickerScreen._fill_list  聯絡人清單過濾邏輯
"""

import json, sys, tempfile
from pathlib import Path

# 讓 tui.py 可以 import（ROOT 路徑操作不影響測試）
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from tui import _ts, _meta, _preview, _save_messages, _load_messages, _MSGS


# ── _ts ──────────────────────────────────────────────────────────

def test_ts_valid():
    # 任意已知 timestamp → HH:MM
    result = _ts("0")
    assert ":" in result, f"expected HH:MM, got {result!r}"

def test_ts_invalid():
    assert _ts("not-a-number") == ""
    assert _ts(None) == ""
    assert _ts("") == ""


# ── _meta ─────────────────────────────────────────────────────────

def test_meta_dict():
    m = {"contentMetadata": {"FILE_NAME": "a.pdf"}}
    assert _meta(m) == {"FILE_NAME": "a.pdf"}

def test_meta_string_repr():
    # messages.json 可能存 Python dict repr
    m = {"contentMetadata": "{'FILE_NAME': 'b.pdf'}"}
    assert _meta(m).get("FILE_NAME") == "b.pdf"

def test_meta_empty():
    assert _meta({}) == {}
    assert _meta({"contentMetadata": None}) == {}

def test_meta_bad_string():
    m = {"contentMetadata": "not-a-dict"}
    assert _meta(m) == {}


# ── _preview ─────────────────────────────────────────────────────

def test_preview_text():
    m = {"contentType": 0, "text": "Hello"}
    assert _preview(m) == "Hello"

def test_preview_text_truncated():
    m = {"contentType": 0, "text": "A" * 50}
    assert len(_preview(m)) <= 40

def test_preview_image():
    assert "圖片" in _preview({"contentType": 1})

def test_preview_video_with_duration():
    m = {"contentType": 2, "contentMetadata": {"DURATION": "30000"}}
    p = _preview(m)
    assert "影片" in p and "30s" in p

def test_preview_video_no_duration():
    assert "影片" in _preview({"contentType": 2})

def test_preview_audio():
    assert "音訊" in _preview({"contentType": 3})

def test_preview_sticker():
    assert "貼圖" in _preview({"contentType": 7})

def test_preview_file_with_name():
    m = {"contentType": 14, "contentMetadata": {"FILE_NAME": "report.pdf"}}
    assert "report.pdf" in _preview(m)

def test_preview_file_no_name():
    assert "檔案" in _preview({"contentType": 14})

def test_preview_location():
    assert "位置" in _preview({"contentType": 15})

def test_preview_unknown_type():
    p = _preview({"contentType": 99})
    assert "99" in p


# ── _save_messages / _load_messages ──────────────────────────────

def test_save_and_load(tmp_path, monkeypatch):
    fake = tmp_path / "messages.json"
    monkeypatch.setattr("tui._MSGS", fake)

    data = {"U123": [{"id": "1", "text": "hi", "createdTime": "1000",
                      "contentType": 0, "from": "U123"}]}
    _save_messages(data)
    assert fake.exists()

    loaded = _load_messages()
    assert loaded == data

def test_load_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("tui._MSGS", tmp_path / "nonexistent.json")
    assert _load_messages() == {}


# ── ChatItem ─────────────────────────────────────────────────────

def test_chat_item_attrs():
    from tui import ChatItem
    item = ChatItem("Uabc", "Alice", "最後一則訊息", 3)
    assert item.mid     == "Uabc"
    assert item.label   == "Alice"
    assert item.preview == "最後一則訊息"
    assert item.unread  == 3

def test_chat_item_no_unread():
    from tui import ChatItem
    item = ChatItem("Uabc", "Bob", "hi")
    assert item.unread == 0


# ── ContactPickerScreen 過濾邏輯 ─────────────────────────────────

def test_picker_builds_all_list():
    from tui import ContactPickerScreen
    contacts = {"Uaaa": "Alice", "Cbbb": "Team A"}
    screen = ContactPickerScreen(contacts, set())
    labels = [d for _, d in screen._all]
    assert any("Alice" in l for l in labels)
    assert any("Team A" in l for l in labels)

def test_picker_group_icon():
    from tui import ContactPickerScreen
    screen = ContactPickerScreen({"Cxxx": "Group"}, set())
    _, display = screen._all[0]
    assert "👥" in display

def test_picker_user_icon():
    from tui import ContactPickerScreen
    screen = ContactPickerScreen({"Uxxx": "Person"}, set())
    _, display = screen._all[0]
    assert "🙍" in display

def test_picker_unknown_mid_fallback():
    from tui import ContactPickerScreen
    screen = ContactPickerScreen({}, {"Uunknown123456789"})
    assert len(screen._all) == 1
    assert "Uunknown" in screen._all[0][1]

def test_picker_filter():
    from tui import ContactPickerScreen
    contacts = {"Ua": "Alice", "Ub": "Bob", "Uc": "Charlie"}
    screen = ContactPickerScreen(contacts, set())
    q = "ali"
    filtered = [(m, d) for m, d in screen._all if q in d.lower() or q in m.lower()]
    assert len(filtered) == 1
    assert "Alice" in filtered[0][1]


# ── 執行 ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest, sys
    sys.exit(pytest.main([__file__, "-v"]))
