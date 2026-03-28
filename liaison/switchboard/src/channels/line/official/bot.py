# /// script
# dependencies = ["playwright", "pillow", "zxing-cpp", "qrcode[pil]"]
# ///
"""
bot.py - LINE 官方帳號 AI 自動回覆

每秒輪詢聊天室，對新的 USER 文字訊息呼叫 claude CLI 產生回覆並送出。

用法：
  uv run bot.py --chat-id <chatId>
  uv run bot.py --chat-id <chatId> --interval 2   # 每 2 秒輪詢一次

停止：Ctrl+C
"""
import argparse, asyncio, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import login, chat_client

CLAUDE_PROMPT = (
    "你是一個AI助理，以下是使用者的訊息，"
    "請幫忙回覆。使用者的訊息是「{text}」"
)


def ask_claude(text: str) -> str:
    """呼叫 claude CLI 產生回覆，回傳純文字。"""
    prompt = CLAUDE_PROMPT.format(text=text)
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI 錯誤: {result.stderr[:200]}")
    return result.stdout.strip()


async def run(args) -> None:
    from playwright.async_api import async_playwright

    session = login.load_session()
    if not session:
        raise RuntimeError("找不到 session，請先執行 uv run login.py")

    chat_id = args.chat_id

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
        print(f"Chat ID: {chat_id}")
        print(f"輪詢間隔: {args.interval}s  |  按 Ctrl+C 停止\n")

        # 取目前最新訊息的 timestamp 作為起始基準
        msgs = await chat_client.get_messages(ctx, xsrf, bot_id, chat_id, limit=1)
        seen_ts = msgs[0]["timestamp"] if msgs else 0
        print(f"起始 timestamp: {seen_ts}")

        while True:
            await asyncio.sleep(args.interval)

            try:
                msgs = await chat_client.get_messages(ctx, xsrf, bot_id, chat_id, limit=10)
            except Exception as e:
                print(f"[poll error] {e}")
                continue

            # 找出所有比 seen_ts 新的 USER 文字訊息（oldest first）
            new_msgs = sorted(
                [m for m in msgs
                 if m["timestamp"] > seen_ts
                 and m.get("source", {}).get("userId") == chat_id  # USER
                 and m.get("message", {}).get("type") == "text"],
                key=lambda m: m["timestamp"],
            )

            for m in new_msgs:
                text = m["message"]["text"].strip()
                ts   = m["timestamp"]
                seen_ts = max(seen_ts, ts)

                print(f"[{ts}] USER: {text}")
                print(f"  → 呼叫 claude...")
                try:
                    reply = ask_claude(text)
                    print(f"  ← {reply[:80]}{'...' if len(reply)>80 else ''}")
                    result = await chat_client.send_message(ctx, xsrf, bot_id, chat_id, reply)
                    if result["status"] != 200:
                        print(f"  送出失敗: {result}")
                except Exception as e:
                    print(f"  [error] {e}")

            if not new_msgs:
                # 更新 seen_ts 為最新訊息的 ts，防止歷史訊息重複處理
                if msgs:
                    seen_ts = max(seen_ts, msgs[0]["timestamp"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="LINE OA AI 自動回覆 bot")
    ap.add_argument("--chat-id",  required=True, help="聊天室 ID")
    ap.add_argument("--interval", type=float, default=1.0, help="輪詢間隔秒數（預設 1）")
    try:
        asyncio.run(run(ap.parse_args()))
    except KeyboardInterrupt:
        print("\n停止。")
