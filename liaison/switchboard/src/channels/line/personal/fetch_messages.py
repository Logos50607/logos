# /// script
# dependencies = ["playwright"]
# ///
"""
fetch_messages.py - 從 LINE GW 直接抓取所有聊天室的完整訊息

原理：
  1. 連接 CDP → 取得 X-Line-Access token
  2. 透過 ltsmSandbox iframe postMessage 計算 HMAC（不需要 Chrome open）
  3. 用 Python 直接呼叫 LINE GW API（getRecentMessagesV2）

用法：
  uv run fetch_messages.py                         # 抓所有聊天室（預設 50 則/室）
  uv run fetch_messages.py --count 200             # 每室 200 則
  uv run fetch_messages.py --chat C4abc... --count 100
  uv run fetch_messages.py --output /tmp/msgs.json
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. parse_args
# 2. fetch_message_boxes(...)    - getMessageBoxes，一次取全部聊天室
# 3. fetch_chat_messages(...)    - getRecentMessagesV2 pagination
# 4. main

import argparse
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from gw_client import EXT_ID, CDP_URL, find_ext_page, get_access_token, compute_hmac, call_api


# ── 1. 參數 ───────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Fetch LINE messages via GW API")
    p.add_argument("--count",  type=int, default=50,   help="每個聊天室抓幾則（預設 50）")
    p.add_argument("--chat",   default=None,            help="指定單一聊天室 mid")
    p.add_argument("--output", type=Path,
                   default=Path(__file__).parent / "messages.json",
                   help="輸出路徑")
    return p.parse_args()


# ── 2. 一次取全部聊天室清單 ──────────────────────────────────────

async def fetch_message_boxes(page, access_token: str,
                               last_msgs: int = 1) -> list[dict]:
    """呼叫 getMessageBoxes，回傳所有 active 聊天室資訊（含 lastMessages）。
    每個 box: {id, unreadCount, lastDeliveredMessageId.deliveredTime, lastMessages}
    """
    path = "/api/talk/thrift/Talk/TalkService/getMessageBoxes"
    params = {
        "activeOnly": True,
        "unreadOnly": False,
        "messageBoxCountLimit": 200,
        "withUnreadCount": True,
        "lastMessagesPerMessageBoxCount": last_msgs,
    }
    body_obj = [params, 2]
    hmac = await compute_hmac(page, access_token, path, json.dumps(body_obj))
    result = call_api(path, body_obj, access_token, hmac)
    if result.get("code") != 0:
        raise RuntimeError(f"getMessageBoxes 失敗: {result}")
    return result["data"]["messageBoxes"]


# ── 3. 抓單一聊天室訊息（含 pagination）────────────────────────────

async def _get_recent(page, access_token, chat_mid, count) -> list:
    path = "/api/talk/thrift/Talk/TalkService/getRecentMessagesV2"
    body_obj = [chat_mid, count]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, access_token, path, body_str)
    result = call_api(path, body_obj, access_token, hmac)
    if result.get('code') != 0:
        return []
    return result.get('data', [])


async def _get_previous(page, access_token, chat_mid, oldest_msg, count) -> list:
    """oldest_msg = {"id": ..., "deliveredTime": ..., "createdTime": ...}"""
    path = "/api/talk/thrift/Talk/TalkService/getPreviousMessagesV2WithRequest"
    body_obj = [{
        "messageBoxId": chat_mid,
        "endMessageId": {
            "messageId": oldest_msg["id"],
            "deliveredTime": oldest_msg.get("deliveredTime") or oldest_msg.get("createdTime"),
        },
        "messagesCount": count,
    }]
    body_str = json.dumps(body_obj)
    hmac = await compute_hmac(page, access_token, path, body_str)
    result = call_api(path, body_obj, access_token, hmac)
    if result.get('code') != 0:
        return []
    return result.get('data', [])


async def fetch_chat_messages(page, access_token: str, chat_mid: str, count: int) -> list:
    """先抓最近 count 則，不夠再往前 paginate"""
    msgs = await _get_recent(page, access_token, chat_mid, count)
    if not msgs:
        return []

    all_msgs = list(msgs)
    page_size = min(count, 50)
    for _ in range(3):
        if len(msgs) < page_size:
            break
        oldest = min(msgs, key=lambda m: int(m.get("createdTime", 0)))
        prev = await _get_previous(page, access_token, chat_mid, oldest, page_size)
        prev = [m for m in prev if m["id"] != oldest["id"]]
        if not prev:
            break
        all_msgs = prev + all_msgs
        msgs = prev

    return all_msgs


# ── 3. 主程式 ─────────────────────────────────────────────────────

async def main():
    args = parse_args()

    async with async_playwright() as p:
        print(f">>> 連接 CDP: {CDP_URL}", flush=True)
        b = await p.chromium.connect_over_cdp(CDP_URL)
        page = find_ext_page(b.contexts[0])

        print(">>> 取得 access token...", flush=True)
        access_token = await get_access_token(page)

        if args.chat:
            chat_mids = [args.chat]
        else:
            captured_path = Path(__file__).parent / "captured.json"
            if not captured_path.exists():
                raise RuntimeError(
                    "找不到 captured.json，請先執行 `uv run capture.py fetch`"
                )
            data = json.loads(captured_path.read_text())
            chat_mids = []
            for r in data:
                if 'getMessageBoxes' in r['url'] and r.get('body', {}).get('code') == 0:
                    boxes = r['body'].get('data', {}).get('messageBoxes', [])
                    chat_mids.extend(box['id'] for box in boxes if 'id' in box)
            chat_mids = list(dict.fromkeys(chat_mids))
            print(f">>> 共 {len(chat_mids)} 個聊天室", flush=True)

        results = {}
        for i, mid in enumerate(chat_mids, 1):
            print(f"  [{i}/{len(chat_mids)}] {mid[:20]}...", flush=True)
            msgs = await fetch_chat_messages(page, access_token, mid, args.count)
            results[mid] = msgs

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        total = sum(len(v) for v in results.values())
        print(f">>> 完成，{total} 則訊息 → {args.output}", flush=True)

        try:
            await b.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
