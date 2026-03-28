"""
chat_client.py - chat.line.biz API 共用工具

對外介面：
  warmup(ctx) → {"xsrf": str, "bot_id": str}
  get_chats(ctx, xsrf, bot_id, limit=25) → list[dict]
  get_messages(ctx, xsrf, bot_id, chat_id, limit=20) → list[dict]
  send_message(ctx, xsrf, bot_id, chat_id, text) → dict
  send_image(ctx, xsrf, bot_id, chat_id, file_path) → dict
  get_streaming_token(ctx, xsrf, bot_id) → dict
"""

# ── 目錄 ─────────────────────────────────────────────────────────
# 1. 常數
# 2. warmup(ctx)
# 3. get_chats
# 4. get_messages
# 5. send_message
# 6. send_image
# 7. get_streaming_token

import json, random, time

BASE = "https://chat.line.biz"


# ── 2. warmup ──────────────────────────────────────────────────

async def warmup(ctx) -> dict:
    """造訪 chat.line.biz 建立 session，回傳 xsrf + bot_id。"""
    page = await ctx.new_page()
    await page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=15000)
    await page.close()

    r = await ctx.request.fetch(f"{BASE}/api/v1/csrfToken")
    xsrf = json.loads(await r.text())["token"]

    r = await ctx.request.fetch(
        f"{BASE}/api/v1/bots?limit=1000",
        headers={"X-XSRF-TOKEN": xsrf, "Origin": BASE},
    )
    bots = json.loads(await r.text()).get("list", [])
    bot_id = bots[0]["botId"] if bots else ""
    return {"xsrf": xsrf, "bot_id": bot_id}


# ── 3. get_chats ───────────────────────────────────────────────

async def get_chats(ctx, xsrf: str, bot_id: str, limit: int = 25) -> list:
    r = await ctx.request.fetch(
        f"{BASE}/api/v2/bots/{bot_id}/chats?folderType=ALL&limit={limit}",
        headers={"X-XSRF-TOKEN": xsrf, "Origin": BASE},
    )
    return json.loads(await r.text()).get("list", [])


# ── 4. get_messages ────────────────────────────────────────────

async def get_messages(ctx, xsrf: str, bot_id: str, chat_id: str,
                       limit: int = 20) -> list:
    r = await ctx.request.fetch(
        f"{BASE}/api/v3/bots/{bot_id}/chats/{chat_id}/messages?limit={limit}",
        headers={"X-XSRF-TOKEN": xsrf, "Origin": BASE},
    )
    return json.loads(await r.text()).get("list", [])


# ── 5. send_message ────────────────────────────────────────────

async def send_message(ctx, xsrf: str, bot_id: str,
                       chat_id: str, text: str) -> dict:
    send_id = f"{chat_id}_{int(time.time() * 1000)}_{random.randint(10000000, 99999999)}"
    body = {"id": "", "type": "textV2", "text": text, "sendId": send_id}
    r = await ctx.request.fetch(
        f"{BASE}/api/v1/bots/{bot_id}/chats/{chat_id}/messages/send",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-XSRF-TOKEN": xsrf,
            "Origin": BASE,
        },
        data=json.dumps(body),
    )
    text_resp = await r.text()
    return {"status": r.status, "body": json.loads(text_resp) if text_resp.strip() else {}}


# ── 6. send_image ─────────────────────────────────────────────

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp"}

async def send_image(ctx, xsrf: str, bot_id: str,
                     chat_id: str, file_path) -> dict:
    """上傳圖片並傳送至指定聊天室。"""
    from pathlib import Path as _Path
    p = _Path(file_path)
    mime = _MIME.get(p.suffix.lower(), "image/jpeg")
    data = p.read_bytes()

    _common = {
        "Referer":                  f"{BASE}/{bot_id}/chat/{chat_id}",
        "Origin":                   BASE,
        "X-Oa-Chat-Client-Version": "20240513144702",
    }

    # Step 1: 上傳檔案（multipart，不加 XSRF）
    r = await ctx.request.fetch(
        f"{BASE}/api/v1/bots/{bot_id}/messages/{chat_id}/uploadFile",
        method="POST",
        headers=_common,
        multipart={"file": {"name": p.name, "mimeType": mime, "buffer": data}},
    )
    resp_text = await r.text()
    if not r.ok:
        return {"status": r.status, "body": resp_text}
    token = json.loads(resp_text)["contentMessageToken"]

    # Step 2: 傳送
    send_id = f"{chat_id}_{int(time.time() * 1000)}_{random.randint(10000000, 99999999)}"
    body = {"items": [{"sendId": send_id, "contentMessageToken": token}]}
    r2 = await ctx.request.fetch(
        f"{BASE}/api/v1/bots/{bot_id}/chats/{chat_id}/messages/bulkSendFiles",
        method="POST",
        headers={**_common, "Content-Type": "application/json", "X-XSRF-TOKEN": xsrf},
        data=json.dumps(body),
    )
    t2 = await r2.text()
    return {"status": r2.status, "body": json.loads(t2) if t2.strip() else {}}


# ── 7. get_streaming_token ─────────────────────────────────────

async def get_streaming_token(ctx, xsrf: str, bot_id: str) -> dict:
    r = await ctx.request.fetch(
        f"{BASE}/api/v1/bots/{bot_id}/streamingApiToken",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-XSRF-TOKEN": xsrf,
            "Origin": BASE,
        },
        data="{}",
    )
    return json.loads(await r.text())
