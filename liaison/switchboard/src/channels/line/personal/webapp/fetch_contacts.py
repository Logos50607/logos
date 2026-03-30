# /// script
# dependencies = ["playwright"]
# ///
"""
fetch_contacts.py - 從 LINE GW API 抓取所有聯絡人與群組顯示名稱，寫入 contacts.json

流程：
  1. getAllContactIds       → 全部好友 mid 清單
  2. getContacts(mids)      → 名字（分批，每批 100）
  3. messages.json C... 鍵  → getGroupsV2 補群組名稱

用法:
  uv run fetch_contacts.py
"""

import asyncio, json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright
from gw_client import CDP_URL, find_ext_page, get_access_token, compute_hmac, call_api

_PATH_ALL_IDS      = "/api/talk/thrift/Talk/TalkService/getAllContactIds"
_PATH_CONTACTS     = "/api/talk/thrift/Talk/TalkService/getContactsV2"
_PATH_GROUPS       = "/api/talk/thrift/Talk/TalkService/getGroupsV2"
_PATH_CHAT_MIDS    = "/api/talk/thrift/Talk/TalkService/getAllChatMids"
_DATA_DIR          = ROOT / "data"
_CONTACTS_JSON     = _DATA_DIR / "friends.json"   # 獨立執行 fetch_contacts.py 時的輸出
_MESSAGES_JSON     = _DATA_DIR / "messages.json"
_BATCH             = 100   # getContacts 每批上限


async def _all_contact_ids(page, token: str) -> list[str]:
    """呼叫 getAllContactIds，回傳全部好友 mid 清單。"""
    body_obj = []
    hmac     = await compute_hmac(page, token, _PATH_ALL_IDS, json.dumps(body_obj))
    result   = call_api(_PATH_ALL_IDS, body_obj, token, hmac)
    if result.get("code") != 0:
        raise RuntimeError(f"getAllContactIds 失敗: {result}")
    ids = result.get("data") or []
    print(f"    getAllContactIds → {len(ids)} 筆", flush=True)
    return [i for i in ids if isinstance(i, str)]


async def _fetch_names(page, token: str, mids: list[str]) -> dict[str, str]:
    """分批呼叫 getContactsV2，回傳 {mid: displayName}。"""
    contacts = {}
    for i in range(0, len(mids), _BATCH):
        batch    = mids[i:i + _BATCH]
        body_obj = [{"targetUserMids": batch}]
        hmac     = await compute_hmac(page, token, _PATH_CONTACTS, json.dumps(body_obj))
        result   = call_api(_PATH_CONTACTS, body_obj, token, hmac)
        # getContactsV2: data.contacts[mid].contact.displayName
        for mid, v in (result.get("data") or {}).get("contacts", {}).items():
            name = (v.get("contact", {}).get("displayName") or "").strip()
            if mid and name:
                contacts[mid] = name
    return contacts


async def _fetch_group_names(page, token: str, group_ids: list[str]) -> dict[str, str]:
    """呼叫 getGroupsV2 取群組名稱。"""
    if not group_ids:
        return {}
    body_obj = [group_ids]
    hmac     = await compute_hmac(page, token, _PATH_GROUPS, json.dumps(body_obj))
    result   = call_api(_PATH_GROUPS, body_obj, token, hmac)
    groups = {}
    for g in result.get("data") or []:
        mid  = g.get("id") or g.get("mid") or ""
        name = (g.get("name") or g.get("displayName") or "").strip()
        if mid and name:
            groups[mid] = name
    return groups


async def _ids_from_path(page, token: str, path: str) -> list[str]:
    """呼叫回傳 ID 清單的 API（泛用）。"""
    body_obj = []
    hmac     = await compute_hmac(page, token, path, json.dumps(body_obj))
    result   = call_api(path, body_obj, token, hmac)
    ids = result.get("data") or []
    return [i for i in ids if isinstance(i, str)]


async def get_all_chat_ids(page, token: str) -> set[str]:
    """回傳所有 1-on-1（U）、群組（C）的 mid 集合。"""
    ids: set[str] = set()

    # 好友
    contacts = await _all_contact_ids(page, token)
    ids.update(contacts)

    # 群組：getAllChatMids → memberChatMids
    try:
        body_obj = []
        hmac     = await compute_hmac(page, token, _PATH_CHAT_MIDS, json.dumps(body_obj))
        result   = call_api(_PATH_CHAT_MIDS, body_obj, token, hmac)
        data     = result.get("data") or {}
        for key in ("memberChatMids", "invitedChatMids"):
            ids.update(m for m in data.get(key, []) if isinstance(m, str))
    except Exception:
        pass

    # 補 messages.json 現有的
    if _MESSAGES_JSON.exists():
        existing = json.loads(_MESSAGES_JSON.read_text())
        ids.update(existing.keys())

    return ids


def _group_ids_from_messages() -> list[str]:
    """從 messages.json 收集 C... 群組 mid（給 fetch_contacts 用）。"""
    if not _MESSAGES_JSON.exists():
        return []
    data = json.loads(_MESSAGES_JSON.read_text())
    return [k for k in data if k.startswith("C") or k.startswith("R")]


async def fetch_contacts(page, token: str | None = None) -> dict[str, str]:
    """回傳 {mid: displayName}（好友 + 群組）。token 可由外部傳入。"""
    if token is None:
        print(">>> 取得 token...", flush=True)
        token = await get_access_token(page)

    print(">>> 取得全部好友 ID...", flush=True)
    all_ids = await _all_contact_ids(page, token)

    print(f">>> 取得 {len(all_ids)} 位好友名稱...", flush=True)
    contacts = await _fetch_names(page, token, all_ids)

    group_ids = list((await get_all_chat_ids(page, token)) - set(all_ids))
    group_ids = [m for m in group_ids if m.startswith("C") or m.startswith("R")]
    if group_ids:
        print(f">>> 取得 {len(group_ids)} 個群組名稱...", flush=True)
        groups = await _fetch_group_names(page, token, group_ids)
        contacts.update(groups)

    print(f"    共取得 {len(contacts)} 筆", flush=True)
    return contacts


async def main():
    async with async_playwright() as pw:
        b    = await pw.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])
        contacts = await fetch_contacts(page)

        if contacts:
            _DATA_DIR.mkdir(exist_ok=True)
            friends_path = _DATA_DIR / "friends.json"
            groups_path  = _DATA_DIR / "groups.json"
            existing_f = json.loads(friends_path.read_text()) if friends_path.exists() else {}
            existing_g = json.loads(groups_path.read_text())  if groups_path.exists()  else {}
            for mid, name in contacts.items():
                if mid.startswith("U"):
                    existing_f[mid] = name
                else:
                    existing_g[mid] = name
            friends_path.write_text(json.dumps(existing_f, ensure_ascii=False, indent=2))
            groups_path.write_text(json.dumps(existing_g,  ensure_ascii=False, indent=2))
            print(f">>> 已儲存 {len(existing_f)} 位好友 → {friends_path}", flush=True)
            print(f">>> 已儲存 {len(existing_g)} 個群組 → {groups_path}", flush=True)
            for mid, name in list(contacts.items())[:8]:
                print(f"    {mid[:20]}… → {name}")
        else:
            print(">>> 沒有取到任何名稱", flush=True)

        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(main())
