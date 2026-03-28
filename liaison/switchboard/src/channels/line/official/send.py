# /// script
# dependencies = ["playwright", "pillow", "zxing-cpp", "qrcode[pil]"]
# ///
"""
send.py - 透過 LINE 官方帳號傳送訊息

用法：
  uv run send.py --chat-id <chatId> --text "訊息內容"

auth 從 session-state.json 讀取（先跑 login.py）
"""
import argparse, asyncio, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import login, chat_client


async def run(args) -> None:
    from playwright.async_api import async_playwright

    session = login.load_session()
    if not session:
        raise RuntimeError("找不到 session，請先執行 uv run login.py")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = await browser.new_context(
            storage_state=session,
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        )

        s = await chat_client.warmup(ctx)
        xsrf, bot_id = s["xsrf"], s["bot_id"]

        result = await chat_client.send_message(ctx, xsrf, bot_id, args.chat_id, args.text)
        if result["status"] == 200:
            print(f">>> 傳送成功")
        else:
            print(f">>> 傳送失敗 HTTP {result['status']}: {result['body']}")
            raise SystemExit(1)

        await browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="透過 LINE OA 傳送訊息")
    ap.add_argument("--chat-id", required=True, help="聊天室 ID")
    ap.add_argument("--text",    required=True, help="訊息內容")
    asyncio.run(run(ap.parse_args()))
