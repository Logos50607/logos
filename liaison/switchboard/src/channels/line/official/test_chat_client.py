# /// script
# dependencies = ["playwright", "pillow", "zxing-cpp", "qrcode[pil]"]
# ///
"""
test_chat_client.py - chat_client + capture + send 端對端測試

驗證：
  1. warmup 取得 xsrf + bot_id
  2. get_chats 回傳聊天室列表
  3. get_messages 回傳訊息列表
  4. send_message 傳送成功
  5. 傳送後 get_messages 可見新訊息
"""
import asyncio, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import login, chat_client


async def main():
    from playwright.async_api import async_playwright

    session = login.load_session()
    assert session, "找不到 session，請先執行 uv run login.py"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(
            storage_state=session,
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        )

        # 1. warmup
        s = await chat_client.warmup(ctx)
        assert s["xsrf"],   "❌ xsrf 為空"
        assert s["bot_id"], "❌ bot_id 為空"
        print(f"[1] warmup ✓  bot_id={s['bot_id'][:12]}...")

        xsrf, bot_id = s["xsrf"], s["bot_id"]

        # 2. get_chats
        chats = await chat_client.get_chats(ctx, xsrf, bot_id)
        assert isinstance(chats, list), "❌ get_chats 非 list"
        assert len(chats) > 0, "❌ 聊天室列表為空"
        chat_id = chats[0]["chatId"]
        print(f"[2] get_chats ✓  {len(chats)} 筆，first={chat_id[:12]}...")

        # 3. get_messages
        msgs = await chat_client.get_messages(ctx, xsrf, bot_id, chat_id)
        assert isinstance(msgs, list), "❌ get_messages 非 list"
        print(f"[3] get_messages ✓  {len(msgs)} 則")

        # 4. send_message
        marker = f"test-{int(time.time())}"
        result = await chat_client.send_message(ctx, xsrf, bot_id, chat_id, marker)
        assert result["status"] == 200, f"❌ send_message HTTP {result['status']}: {result['body']}"
        print(f"[4] send_message ✓  marker={marker}")

        # 5. 確認訊息可讀回
        await asyncio.sleep(1)
        msgs2 = await chat_client.get_messages(ctx, xsrf, bot_id, chat_id, limit=5)
        texts = [m.get("message", {}).get("text", "") for m in msgs2]
        assert marker in texts, f"❌ 傳送後讀不到訊息，texts={texts}"
        print(f"[5] round-trip ✓  marker found in messages")

        await browser.close()

    print("\n✅ 所有測試通過")


if __name__ == "__main__":
    asyncio.run(main())
