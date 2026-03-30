"""
test_fetch_contacts.py - fetch_contacts.py 輔助函式單元測試

測試範圍（不需要 LINE / CDP）：
  - _group_ids_from_messages   從 messages.json 撈群組 ID
  - _fetch_names 回傳格式解析  模擬 API response
  - _fetch_group_names 解析    模擬 API response
"""

import json, sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from fetch_contacts import _group_ids_from_messages, _fetch_names, _fetch_group_names


# ── _group_ids_from_messages ─────────────────────────────────────

def test_group_ids_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("fetch_contacts._MESSAGES_JSON", tmp_path / "none.json")
    assert _group_ids_from_messages() == []

def test_group_ids_extracts_c_prefix(tmp_path, monkeypatch):
    f = tmp_path / "messages.json"
    f.write_text(json.dumps({
        "Uabc": [],
        "Cgroup1": [],
        "Cgroup2": [],
        "Rabc": [],
    }))
    monkeypatch.setattr("fetch_contacts._MESSAGES_JSON", f)
    ids = _group_ids_from_messages()
    assert set(ids) == {"Cgroup1", "Cgroup2"}

def test_group_ids_no_groups(tmp_path, monkeypatch):
    f = tmp_path / "messages.json"
    f.write_text(json.dumps({"Uabc": [], "Udef": []}))
    monkeypatch.setattr("fetch_contacts._MESSAGES_JSON", f)
    assert _group_ids_from_messages() == []


# ── _fetch_names ─────────────────────────────────────────────────

async def _fake_hmac(*a, **kw): return "fake-hmac"

def _mock_call_api_contacts(path, body, token, hmac):
    batch = body[0]
    return {"code": 0, "data": [
        {"mid": m, "displayName": f"Name-{m[-4:]}"} for m in batch
    ]}

def test_fetch_names_basic():
    import asyncio
    page = MagicMock()
    mids = ["Uaaaa", "Ubbbb", "Ucccc"]
    with patch("fetch_contacts.compute_hmac", new=AsyncMock(return_value="h")), \
         patch("fetch_contacts.call_api", side_effect=_mock_call_api_contacts):
        result = asyncio.run(_fetch_names(page, "tok", mids))
    assert len(result) == 3
    assert result["Uaaaa"] == "Name-aaaa"

def test_fetch_names_batches():
    """確認超過 _BATCH 時分批呼叫。"""
    import asyncio
    import fetch_contacts as fc
    page = MagicMock()
    mids = [f"U{i:04d}" for i in range(250)]
    calls = []
    def spy_call(path, body, token, hmac):
        calls.append(len(body[0]))
        return {"code": 0, "data": [
            {"mid": m, "displayName": f"N{m}"} for m in body[0]
        ]}
    with patch("fetch_contacts.compute_hmac", new=AsyncMock(return_value="h")), \
         patch("fetch_contacts.call_api", side_effect=spy_call):
        result = asyncio.run(_fetch_names(page, "tok", mids))
    assert len(result) == 250
    assert all(n <= fc._BATCH for n in calls), "每批不超過 _BATCH"

def test_fetch_names_skips_empty():
    import asyncio
    page = MagicMock()
    def api(path, body, token, hmac):
        return {"code": 0, "data": [
            {"mid": "Uaaa", "displayName": ""},     # 空名字 → 跳過
            {"mid": "",     "displayName": "Ghost"}, # 空 mid → 跳過
            {"mid": "Ubbb", "displayName": "Bob"},
        ]}
    with patch("fetch_contacts.compute_hmac", new=AsyncMock(return_value="h")), \
         patch("fetch_contacts.call_api", side_effect=api):
        result = asyncio.run(_fetch_names(page, "tok", ["Uaaa", "Ubbb"]))
    assert "Uaaa" not in result
    assert result.get("Ubbb") == "Bob"


# ── _fetch_group_names ───────────────────────────────────────────

def test_fetch_group_names_empty():
    import asyncio
    page = MagicMock()
    result = asyncio.run(_fetch_group_names(page, "tok", []))
    assert result == {}

def test_fetch_group_names_parses_name():
    import asyncio
    page = MagicMock()
    def api(path, body, token, hmac):
        return {"code": 0, "data": [
            {"id": "Cgrp1", "name": "工作群"},
            {"id": "Cgrp2", "name": "家族"},
        ]}
    with patch("fetch_contacts.compute_hmac", new=AsyncMock(return_value="h")), \
         patch("fetch_contacts.call_api", side_effect=api):
        result = asyncio.run(_fetch_group_names(page, "tok", ["Cgrp1", "Cgrp2"]))
    assert result == {"Cgrp1": "工作群", "Cgrp2": "家族"}


if __name__ == "__main__":
    import pytest, sys
    sys.exit(pytest.main([__file__, "-v"]))
