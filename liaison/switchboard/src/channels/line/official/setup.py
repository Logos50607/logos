# /// script
# dependencies = ["playwright", "pillow"]
# ///
"""
setup.py - LINE 官方帳號設定精靈

用法:
  uv run setup.py [--provider NAME] [--channel NAME]
                  [--email EMAIL] [--webhook-url URL]
                  [--qr-port PORT]

步驟:
  1. 啟動 headless 瀏覽器
  2. 登入 LINE Developers Console（QR code 掃描）
  3. 建立或選取 Provider 與 Messaging API Channel
  4. 取得並儲存 Channel Secret & Channel Access Token
  5. 設定 Webhook URL（可選）
"""
import argparse, asyncio, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import credentials, login, console, webhook


async def main(args: argparse.Namespace) -> None:
    import json
    from playwright.async_api import async_playwright

    provider    = args.provider     or _prompt("Provider 名稱（英文）")
    channel     = args.channel      or _prompt("Channel 名稱（英文）")
    email       = args.email        or _prompt("聯絡 Email")
    webhook_url = args.webhook_url  # 可為空，稍後可單獨設定

    api_log: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx     = await browser.new_context(storage_state=login.load_session())
        page    = await ctx.new_page()

        # --sniff：錄下所有非 GET 的 API 請求，供後續改寫成純 API 呼叫
        if args.sniff:
            from urllib.parse import urlparse
            def _log_req(req):
                host = urlparse(req.url).hostname or ""
                if "line.biz" not in host or req.method in ("GET", "OPTIONS"):
                    return
                entry = {"method": req.method, "url": req.url,
                         "headers": dict(req.headers), "body": req.post_data}
                api_log.append(entry)
                print(f"  [API] {req.method} {req.url}")
            page.on("request", _log_req)

        # 1. 登入
        await login.ensure_logged_in(page, args.qr_port)

        # 2. Provider + Channel + 取憑證
        creds = await console.ensure_channel(page, provider, channel, email)
        print(f"\n>>> 憑證取得完成")
        print(f"    Channel ID：{creds['channel_id']}")

        # 3. 儲存憑證
        credentials.save(creds["channel_secret"], creds["channel_token"])

        # 4. Webhook（可選）
        if webhook_url:
            await webhook.configure(page, creds["channel_id"], webhook_url)
        else:
            print("\n>>> 跳過 Webhook 設定（未提供 --webhook-url）")
            print(    "    如需設定，執行：")
            print(f"    uv run setup.py --webhook-url https://your.server/webhook")

        await browser.close()

    if args.sniff and api_log:
        import json
        out = "/tmp/api-log.json"
        Path(out).write_text(json.dumps(api_log, indent=2, ensure_ascii=False))
        print(f"\n>>> API log 已儲存：{out}（共 {len(api_log)} 筆）")

    print("\n>>> 設定完成！目前憑證：")
    credentials.show()


def _prompt(label: str) -> str:
    val = input(f"  {label}：").strip()
    if not val:
        return _prompt(label)
    return val


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="LINE 官方帳號設定精靈")
    ap.add_argument("--provider",    default="", help="Provider 名稱（英文）")
    ap.add_argument("--channel",     default="", help="Messaging API Channel 名稱")
    ap.add_argument("--email",       default="", help="聯絡 Email（channel 建立必填）")
    ap.add_argument("--webhook-url", default="", help="Webhook URL（可選）")
    ap.add_argument("--qr-port",     type=int, default=8889, help="QR 圖片 HTTP port")
    ap.add_argument("--sniff",       action="store_true", help="錄下 API 請求至 /tmp/api-log.json")
    asyncio.run(main(ap.parse_args()))
