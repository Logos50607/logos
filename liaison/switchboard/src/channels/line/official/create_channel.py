# /// script
# dependencies = ["playwright", "qrcode[pil]", "zxing-cpp", "pillow"]
# ///
"""
create_channel.py - 建立 LINE 官方帳號 + Messaging API Channel

用法 A（已有 OA ID，最常用）：
  uv run create_channel.py --oa-id <botId> --provider-id 2005000564 \
                           [--webhook-url https://your.server/webhook]

用法 B（完整流程，需要有頭瀏覽器）：
  # ssh -X 進入後執行：
  uv run create_channel.py --name "MyBot" --email "me@example.com" \
                           --provider-id 2005000564 --headed \
                           [--webhook-url https://your.server/webhook]

  # 腳本會自動填表單、跳到確認頁，此時需手動點「完成」（reCAPTCHA）
  # 完成後腳本自動繼續 Messaging API 設定

auth 從 session-state.json 讀取（先跑 login.py 登入一次）
"""
import argparse, asyncio, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import login, credentials as creds_module

_FORM_URL       = "https://entry.line.biz/form/entry/unverified"
_CATEGORY_GROUP = "88"   # 其他在地店家
_CATEGORY       = "952"  # 在地店家（其他）


# ── OA 建立（有頭瀏覽器）───────────────────────────────────────────

async def create_oa_headed(page, name: str, email: str) -> str:
    """填表單 → 等使用者手動點「完成」→ 回傳 oa_id"""
    print(f">>> 開啟建立表單：{_FORM_URL}")
    await page.goto(_FORM_URL, wait_until="networkidle", timeout=20000)
    await asyncio.sleep(1)

    print(f">>> 填入帳號名稱：{name}")
    await page.fill('input[name="bot.name"]', name)
    await page.fill('input[name="account.email"]', email)

    try:
        await page.select_option('select[name="legalCountryCode"]', "TW")
    except Exception:
        pass

    await asyncio.sleep(0.5)
    await page.evaluate(f"""() => {{
        const el = document.querySelector('[name="category_group"]');
        if (el) {{ el.value = '{_CATEGORY_GROUP}';
                   el.dispatchEvent(new Event('change', {{bubbles:true}})); }}
    }}""")
    await asyncio.sleep(1)
    await page.evaluate(f"""() => {{
        const el = document.querySelector('[name="category"]');
        if (el) {{ el.value = '{_CATEGORY}';
                   el.dispatchEvent(new Event('change', {{bubbles:true}})); }}
    }}""")
    await asyncio.sleep(2)

    print(">>> 自動點確定（進入確認頁）...")
    await page.click('button:has-text("確定")', timeout=5000)
    await page.wait_for_url("**/confirmation", timeout=10000)
    print(f"\n{'━'*60}")
    print(f"  ▶ 確認頁已開啟：{page.url}")
    print(f"  請在瀏覽器視窗中點擊「完成」按鈕（須通過 reCAPTCHA）")
    print(f"{'━'*60}\n")

    # 等待 create API 回應
    oa_id_holder: dict = {}
    async def _on_resp(resp):
        if "unverified/create" in resp.url and resp.status == 200:
            try:
                data = await resp.json()
                oa_id = (data.get("botId") or data.get("id")
                         or data.get("serviceAccountId"))
                if oa_id:
                    oa_id_holder["id"] = str(oa_id)
                    print(f">>> OA 建立成功：{oa_id}")
            except Exception:
                pass
    page.on("response", _on_resp)

    # 等最多 120 秒讓使用者完成 reCAPTCHA
    for _ in range(60):
        await asyncio.sleep(2)
        if oa_id_holder.get("id"):
            break
        if "confirmation" not in page.url:
            break  # 頁面跳走了
    else:
        raise RuntimeError("等待 OA 建立逾時（120s），請確認 reCAPTCHA 已通過")

    oa_id = oa_id_holder.get("id")
    if not oa_id:
        raise RuntimeError(f"OA 建立失敗，目前 URL：{page.url}")
    return oa_id


# ── API 步驟（純 API，無 reCAPTCHA）────────────────────────────────

async def _xsrf(ctx, url: str) -> str:
    cookies = await ctx.cookies([url])
    return next((c["value"] for c in cookies if c["name"] == "XSRF-TOKEN"), "")


async def _agree_notices(ctx, oa_id: str, xsrf: str) -> None:
    """同意 manager.line.biz 的服務條款（notices 2 & 4）"""
    headers = {"X-XSRF-TOKEN": xsrf, "Origin": "https://manager.line.biz"}
    redirect = f"/account/{oa_id}/"
    for notice_id in (2, 4):
        url = (f"https://manager.line.biz/api/bots/{oa_id}/notices/{notice_id}/agree"
               f"?redirectUri={redirect}")
        r = await ctx.request.fetch(url, method="PUT", headers=headers, data="{}")
        print(f">>> notices/{notice_id}/agree: {r.status}")


async def enable_messaging_api(ctx, oa_id: str, provider_id: int) -> str | None:
    xsrf = await _xsrf(ctx, "https://manager.line.biz")
    headers = {"Content-Type": "application/json",
               "X-XSRF-TOKEN": xsrf,
               "Origin": "https://manager.line.biz"}

    # 先同意條款（新 OA 必須）
    await _agree_notices(ctx, oa_id, xsrf)

    resp = await ctx.request.fetch(
        f"https://manager.line.biz/api/bots/{oa_id}/enableMessagingApi",
        method="POST", headers=headers,
        data=json.dumps({"providerId": provider_id}),
    )
    text = await resp.text()
    if not resp.ok:
        raise RuntimeError(f"enableMessagingApi HTTP {resp.status}: {text}")
    data = json.loads(text) if text.strip() else {}
    print(f">>> enableMessagingApi: {json.dumps(data)[:200]}")
    # 回傳可能為空；改用 channel list 查詢
    return str(data.get("channelId") or data.get("id") or "")


async def find_channel_id(ctx, provider_id: int, oa_basic_id: str) -> str:
    """從 provider channel list 找出對應 OA 的 channel ID"""
    r = await ctx.request.fetch(
        f"https://developers.line.biz/api/v1/channel/?providerId={provider_id}")
    if not r.ok:
        return ""
    channels = (json.loads(await r.text())).get("values", [])
    for ch in channels:
        bot_cfg = ch.get("botConfiguration", {})
        if bot_cfg.get("basicId") == oa_basic_id:
            return str(ch["id"])
    # fallback：回傳最新建立的 BOT channel
    bots = [c for c in channels if "BOT" in c.get("productTypes", [])]
    bots.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
    return str(bots[0]["id"]) if bots else ""


async def get_channel_info(ctx, channel_id: str) -> dict:
    resp = await ctx.request.fetch(
        f"https://developers.line.biz/api/v1/channel/{channel_id}",
        method="GET",
    )
    text = await resp.text()
    if not resp.ok:
        print(f">>> get_channel_info HTTP {resp.status}: {text[:200]}")
        return {}
    data = json.loads(text) if text.strip() else {}
    print(f">>> channel secret: {data.get('secret','(not found)')}")
    return data


def issue_access_token(channel_id: str, secret: str) -> str:
    """用 channel_id + secret 換取 long-term access token"""
    import urllib.request, urllib.parse
    body = urllib.parse.urlencode({
        "grant_type":    "client_credentials",
        "client_id":     channel_id,
        "client_secret": secret,
    }).encode()
    req = urllib.request.Request(
        "https://api.line.me/v2/oauth/accessToken",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read()).get("access_token", "")


async def set_webhook(ctx, oa_id: str, webhook_url: str) -> None:
    xsrf = await _xsrf(ctx, "https://manager.line.biz")
    headers = {"Content-Type": "application/json",
               "X-XSRF-TOKEN": xsrf,
               "Origin": "https://manager.line.biz"}
    for url, body in [
        (f"https://manager.line.biz/api/v2/bots/{oa_id}/registerWebhookEndpoint",
         {"endpoint": webhook_url}),
        (f"https://manager.line.biz/api/v2/bots/{oa_id}/responseSettings/enabledWebhook",
         {"enabled": True}),
    ]:
        r = await ctx.request.fetch(url, method="POST", headers=headers,
                                    data=json.dumps(body))
        if not r.ok:
            print(f"    警告: {url} → {r.status}")
    print(f">>> Webhook 已設定：{webhook_url}")


# ── 主流程 ─────────────────────────────────────────────────────────

async def run(args) -> None:
    from playwright.async_api import async_playwright

    session = login.load_session()
    if not session:
        raise RuntimeError("找不到 session，請先執行 uv run login.py")

    headless = not getattr(args, "headed", False)
    oa_id    = getattr(args, "oa_id", None)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = await browser.new_context(
            storage_state=session,
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 800},
        )

        # 預先造訪各 domain 建立 session & XSRF-TOKEN
        page = await ctx.new_page()
        for warmup in ["https://manager.line.biz/", "https://developers.line.biz/console/"]:
            await page.goto(warmup, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(1)

        # 1. 建立 OA（可選）
        if not oa_id:
            if not getattr(args, "name", None):
                raise RuntimeError("需提供 --name 與 --email，或用 --oa-id 跳過 OA 建立")
            oa_id = await create_oa_headed(page, args.name, args.email)

        print(f"\n>>> OA ID：{oa_id}")

        # 2. 開啟 Messaging API
        print(f">>> 開啟 Messaging API（provider: {args.provider_id}）")
        channel_id = await enable_messaging_api(ctx, oa_id, int(args.provider_id))

        # enableMessagingApi 回傳空時，從 channel list 找 ID
        if not channel_id:
            print(f">>> 從 channel list 搜尋（oa: {oa_id}）")
            channel_id = await find_channel_id(ctx, int(args.provider_id), oa_id)
            print(f">>> channel ID：{channel_id}")

        # 3. 取 Channel Secret & Token
        ch_info = {}
        if channel_id:
            ch_info = await get_channel_info(ctx, channel_id)

        # 4. Webhook
        if getattr(args, "webhook_url", ""):
            await set_webhook(ctx, oa_id, args.webhook_url)

        # 5. 儲存憑證
        secret = ch_info.get("secret") or ch_info.get("channelSecret") or ""
        # access token 需另外用 OAuth API 發行
        token = ""
        if secret and channel_id:
            print(">>> 發行 Channel Access Token...")
            token = issue_access_token(channel_id, secret)
        if secret and token:
            creds_module.save(secret, token)
            print(">>> 憑證已儲存")
            creds_module.show()
        else:
            print(f">>> 憑證尚未取得 secret={secret!r} token={token!r}")

        await browser.close()
        print("\n>>> 完成！")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="LINE OA + Messaging API 設定")
    # 建立 OA 用
    ap.add_argument("--name",        default="", help="OA 名稱（新建 OA 時必填）")
    ap.add_argument("--email",       default="", help="聯絡 Email（新建 OA 時必填）")
    ap.add_argument("--headed",      action="store_true",
                    help="有頭模式（建立 OA 需要，配合 ssh -X 或本地 DISPLAY 使用）")
    # 跳過 OA 建立
    ap.add_argument("--oa-id",       default="", help="已有的 OA botId（跳過 OA 建立）")
    # 共用
    ap.add_argument("--provider-id", required=True, help="Provider ID")
    ap.add_argument("--webhook-url", default="",    help="Webhook URL（可選）")
    asyncio.run(run(ap.parse_args()))
