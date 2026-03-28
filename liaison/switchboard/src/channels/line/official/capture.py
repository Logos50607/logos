# /// script
# dependencies = ["playwright", "pillow", "zxing-cpp", "qrcode[pil]"]
# ///
"""
capture.py - 讀取 LINE 官方帳號聊天訊息

用法：
  uv run capture.py                          # 列出所有聊天室
  uv run capture.py --chat-id <chatId>       # 列出該聊天室最近訊息
  uv run capture.py --chat-id <chatId> --limit 50

auth 從 session-state.json 讀取（先跑 login.py）
"""
import argparse, asyncio, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import login, chat_client


def _fmt_msg(entry: dict) -> str:
    ts    = entry.get("timestamp", 0) // 1000
    msg   = entry.get("message", {})
    mtype = msg.get("type", "?")
    text  = msg.get("text", "")
    src   = entry.get("source", {})
    who   = "USER" if src.get("userId") == src.get("chatId") else "BOT"
    if mtype == "text":
        return f"[{ts}] {who}: {text}"
    return f"[{ts}] {who}: ({mtype})"


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
        print(f"Bot ID: {bot_id}")

        if not args.chat_id:
            chats = await chat_client.get_chats(ctx, xsrf, bot_id)
            print(f"\n聊天室列表（{len(chats)} 筆）：")
            for c in chats:
                p_name = c.get("profile", {}).get("name", "?")
                cid    = c["chatId"]
                unread = "" if c.get("read") else " [未讀]"
                print(f"  {cid}  {p_name}{unread}")
        else:
            msgs = await chat_client.get_messages(
                ctx, xsrf, bot_id, args.chat_id, args.limit)
            print(f"\n最近 {len(msgs)} 則訊息（chat: {args.chat_id[:16]}...）：")
            for m in msgs:
                print(_fmt_msg(m))

        await browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="讀取 LINE OA 聊天訊息")
    ap.add_argument("--chat-id", default="", help="聊天室 ID（空則列出所有聊天室）")
    ap.add_argument("--limit",   type=int, default=20, help="讀取筆數（預設 20）")
    asyncio.run(run(ap.parse_args()))
