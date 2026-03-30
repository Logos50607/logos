# /// script
# dependencies = ["playwright"]
# ///
"""
fetch_contacts.py - 從 LINE GW API 抓取聯絡人顯示名稱，寫入 contacts.json

用法:
  uv run fetch_contacts.py
"""

import asyncio, json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright
from gw_client import CDP_URL, find_ext_page, get_access_token, compute_hmac, call_api

_PATH_CONTACTS = "/api/talk/thrift/Talk/TalkService/getContacts"
_CONTACTS_JSON = Path(__file__).parent / "contacts.json"
_MESSAGES_JSON = ROOT / "messages.json"


def _collect_mids() -> list[str]:
    """從 messages.json 收集所有 1-on-1 chat mids（U 開頭）。"""
    if not _MESSAGES_JSON.exists():
        return []
    data = json.loads(_MESSAGES_JSON.read_text())
    mids = set()
    for chat_mid in data:
        if chat_mid.startswith("U"):
            mids.add(chat_mid)
        # 也收 from 欄位（對方 mid）
        for m in data[chat_mid]:
            frm = m.get("from", "")
            if frm.startswith("U"):
                mids.add(frm)
    return list(mids)


async def fetch_contacts(page, token: str | None = None) -> dict[str, str]:
    """回傳 {mid: displayName}。token 可由外部傳入以避免重複 reload。"""
    mids = _collect_mids()
    if not mids:
        print("messages.json 沒有資料", flush=True)
        return {}

    if token is None:
        print(f">>> 取得 token...", flush=True)
        token = await get_access_token(page)

    print(f">>> 查詢 {len(mids)} 個聯絡人...", flush=True)
    # getContacts 接受 mid 列表
    body_obj = [mids]
    body_str = json.dumps(body_obj)
    hmac     = await compute_hmac(page, token, _PATH_CONTACTS, body_str)
    result   = call_api(_PATH_CONTACTS, body_obj, token, hmac)

    if result.get("code") != 0:
        print(f"getContacts 失敗: {result}", flush=True)
        return {}

    contacts = {}
    for c in result.get("data") or []:
        mid  = c.get("mid") or c.get("id") or ""
        name = (c.get("displayName") or c.get("name") or "").strip()
        if mid and name:
            contacts[mid] = name

    return contacts


async def main():
    async with async_playwright() as pw:
        b    = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        contacts = await fetch_contacts(page)

        if contacts:
            existing = {}
            if _CONTACTS_JSON.exists():
                existing = json.loads(_CONTACTS_JSON.read_text())
            existing.update(contacts)
            _CONTACTS_JSON.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2))
            print(f">>> 已儲存 {len(contacts)} 筆到 {_CONTACTS_JSON}", flush=True)
            for mid, name in list(contacts.items())[:5]:
                print(f"    {mid[:20]}… → {name}")
        else:
            print(">>> 沒有取到任何名稱", flush=True)

        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(main())
