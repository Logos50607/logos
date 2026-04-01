# /// script
# dependencies = ["playwright"]
# ///
"""
sync.py - LINE 個人帳號背景同步 daemon

每隔 POLL_INTERVAL 秒：
  1. 處理 outbox.json（發送待送訊息 / 收回）
  2. fetch_message_boxes → 找出有新訊息的聊天室
  3. fetch_chat_messages → 抓新訊息，合併 messages.json
  4. decrypt_pending → E2EE 解密
  5. sync_contacts → 補聯絡人名稱

SSOT 寫入：
  data/messages.json  data/friends.json  data/groups.json
  data/pubkeys.json   data/state.json    data/outbox.json

用法：
  uv run sync.py
  uv run sync.py --interval 10
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. 常數 & 路徑
# 2. _write_atomic / _read_json / _ts
# 3. _refresh_token(page, ctx)
# 4. _process_outbox(page, ctx)
# 5. _fetch_messages(page, ctx)
# 6. _decrypt_pending(page, ctx)
# 7. _sync_contacts(page, ctx)
# 8. main()

import argparse, asyncio, json, sys, time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from gw_client import CDP_URL, find_ext_page, get_access_token

_DATA    = Path(__file__).parent / "data"
_MSGS    = _DATA / "messages.json"
_FRIENDS = _DATA / "friends.json"
_GROUPS  = _DATA / "groups.json"
_PUBKEYS = _DATA / "pubkeys.json"
_OUTBOX     = _DATA / "outbox.json"
_STATE      = _DATA / "state.json"
_TUI_ACTIVE = _DATA / "tui_active"

POLL_INTERVAL_ACTIVE = 5    # TUI 開著時
POLL_INTERVAL_IDLE   = 600  # TUI 關閉時（10 分鐘）


# ── 2. 工具 ───────────────────────────────────────────────────────

def _write_atomic(path: Path, obj) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    tmp.rename(path)

def _read_json(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ── 3. Token 管理 ─────────────────────────────────────────────────

async def _refresh_token(page, ctx: dict) -> None:
    """Token 超過 1 小時才 reload 重取。"""
    if ctx["token"] and time.time() - ctx["token_ts"] < 3600:
        return
    ctx["token"]    = await get_access_token(page)
    ctx["token_ts"] = time.time()
    print(f"[{_ts()}] token 已更新", flush=True)


# ── 4. 處理 outbox（發送 / 收回）────────────────────────────────

async def _process_outbox(page, ctx: dict) -> None:
    if not _OUTBOX.exists():
        return
    outbox = json.loads(_OUTBOX.read_text())
    if not outbox:
        return

    from send_api import send_e2ee_text, unsend_message
    msgs      = ctx["messages"]
    remaining = []
    changed   = False

    for item in outbox:
        retries = item.get("_retries", 0)
        if retries >= 3:
            continue  # 已放棄

        if item.get("action") == "unsend":
            r = await unsend_message(page, item["msg_id"], _token=ctx["token"])
            if r.get("ok"):
                mid = item.get("mid", "")
                for m in msgs.get(mid, []):
                    if m.get("id") == item["msg_id"]:
                        m["_unsent"] = True
                        break
                changed = True
                print(f"[{_ts()}] 已收回 {item['msg_id'][:12]}", flush=True)
            else:
                item["_retries"] = retries + 1
                remaining.append(item)
            continue

        # send
        to, text = item.get("to", ""), item.get("text", "")
        r = await send_e2ee_text(
            page, to, text,
            reply_to_id=item.get("reply_to_id"),
            _token=ctx["token"], _my_mid=ctx["my_mid"], _sender_key_id=ctx["key_id"],
        )
        if r.get("ok"):
            # 不寫入 messages.json，讓 _fetch_messages 抓 LINE server 回來的真實 ID
            # 避免 local_id 與 server ID 同時存在造成 duplicate
            print(f"[{_ts()}] 已發送 → {to[:12]}: {text[:20]}", flush=True)
        else:
            item["_retries"] = retries + 1
            remaining.append(item)
            print(f"[{_ts()}] 發送失敗 (retry {retries+1}): {r.get('error')}", flush=True)

    _OUTBOX.write_text(json.dumps(remaining, ensure_ascii=False))
    if changed:
        _write_atomic(_MSGS, msgs)


# ── 5. 抓新訊息 ───────────────────────────────────────────────────

async def _fetch_messages(page, ctx: dict) -> None:
    from fetch_messages import fetch_message_boxes, fetch_chat_messages
    token   = ctx["token"]
    msgs    = ctx["messages"]
    boxes   = await fetch_message_boxes(page, token, last_msgs=1)
    changed = False
    for box in boxes:
        mid       = box["id"]
        last_id   = (box.get("lastDeliveredMessageId") or {}).get("messageId")
        local_ids = {m["id"] for m in msgs.get(mid, [])}
        if not last_id or last_id in local_ids:
            continue
        fresh = await fetch_chat_messages(page, token, mid, 30)
        new   = [m for m in fresh if m["id"] not in local_ids]
        if new:
            msgs.setdefault(mid, []).extend(new)
            changed = True
            print(f"[{_ts()}] {mid[:12]} +{len(new)} 則", flush=True)
    if changed:
        _write_atomic(_MSGS, msgs)


# ── 6. 解密 E2EE ─────────────────────────────────────────────────

async def _decrypt_pending(page, ctx: dict) -> None:
    from send_api import decrypt_e2ee_message
    msgs    = ctx["messages"]
    pending = [
        (mid, m) for mid, chat in msgs.items() for m in chat
        if m.get("chunks") and m.get("text") is None and not m.get("_decrypt_skip")
    ]
    if not pending:
        return
    ok = fail = 0
    for mid, m in pending:
        text = await decrypt_e2ee_message(
            page, m, ctx["my_mid"], ctx["token"],
            ctx["ltsm_cache"], ctx["chan_cache"], ctx["pub_store"],
        )
        if text is not None:
            m["text"] = text
            ok += 1
        else:
            fail += 1
    if ok:
        print(f"[{_ts()}] 解密 {ok} 則成功，{fail} 則失敗", flush=True)
        _write_atomic(_MSGS, msgs)
        _write_atomic(_PUBKEYS, ctx["pub_store"])


# ── 7. 同步聯絡人 ────────────────────────────────────────────────

async def _sync_contacts(page, ctx: dict) -> None:
    from webapp.fetch_contacts import _fetch_names, _fetch_group_names
    contacts = ctx["contacts"]
    missing  = [mid for mid in ctx["messages"] if mid not in contacts]
    if not missing:
        return
    token = ctx["token"]
    new   = {}
    if u := [m for m in missing if m.startswith("U")]:
        new.update(await _fetch_names(page, token, u))
    if g := [m for m in missing if m.startswith("C") or m.startswith("R")]:
        new.update(await _fetch_group_names(page, token, g))
    if new:
        contacts.update(new)
        _write_atomic(_FRIENDS, {k: v for k, v in contacts.items() if k.startswith("U")})
        _write_atomic(_GROUPS,  {k: v for k, v in contacts.items()
                                  if k.startswith("C") or k.startswith("R")})
        print(f"[{_ts()}] 聯絡人 +{len(new)} 筆", flush=True)


# ── 8. 主程式 ─────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="LINE sync daemon")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL_ACTIVE, help="TUI 開啟時的輪詢間隔秒數")
    args = parser.parse_args()

    async with async_playwright() as pw:
        print(f"[{_ts()}] 連接 CDP: {CDP_URL}", flush=True)
        browser = await pw.chromium.connect_over_cdp(CDP_URL)
        page    = find_ext_page(browser.contexts[0])

        from send_api import get_my_info
        from encrypt_e2ee import load_idb_pubkeys

        print(f"[{_ts()}] 取得 token（reload 頁面，等待 LTSM sandbox 初始化）...", flush=True)
        token          = await get_access_token(page)
        print(f"[{_ts()}] 讀取 my_mid / key_id...", flush=True)
        my_mid, key_id = await get_my_info(page)
        print(f"[{_ts()}] mid={my_mid[:20]}... key={key_id}", flush=True)

        contacts  = {}
        for p in (_FRIENDS, _GROUPS):
            if p.exists():
                contacts.update(json.loads(p.read_text()))

        pub_store = _read_json(_PUBKEYS, {})
        pub_store.update(await load_idb_pubkeys(page))

        ctx = {
            "token":      token,
            "token_ts":   time.time(),
            "my_mid":     my_mid,
            "key_id":     key_id,
            "messages":   _read_json(_MSGS, {}),
            "contacts":   contacts,
            "pub_store":  pub_store,
            "ltsm_cache": {},
            "chan_cache":  {},
        }

        _DATA.mkdir(exist_ok=True)
        _write_atomic(_STATE, {"my_mid": my_mid, "key_id": key_id, "ts": int(time.time())})
        print(f"[{_ts()}] 開始輪詢（TUI 開啟時 {POLL_INTERVAL_ACTIVE}s，閒置時 {POLL_INTERVAL_IDLE}s）", flush=True)

        _last_mode = None
        while True:
            tui_active = _TUI_ACTIVE.exists()
            interval   = POLL_INTERVAL_ACTIVE if tui_active else POLL_INTERVAL_IDLE
            if tui_active != _last_mode:
                mode_str = "高頻" if tui_active else "閒置"
                print(f"[{_ts()}] 切換為{mode_str}模式（每 {interval}s）", flush=True)
                _last_mode = tui_active
            try:
                await _refresh_token(page, ctx)
                await _process_outbox(page, ctx)
                await _fetch_messages(page, ctx)
                await _decrypt_pending(page, ctx)
                await _sync_contacts(page, ctx)
                _write_atomic(_STATE, {"my_mid": my_mid, "key_id": key_id, "ts": int(time.time())})
            except Exception as e:
                print(f"[{_ts()}] 輪詢失敗: {e}", flush=True)
            await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
