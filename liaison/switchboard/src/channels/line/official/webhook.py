"""
webhook.py - LINE Messaging API Webhook 設定

對外介面:
  configure(page, channel_id, webhook_url)  設定 URL、啟用 webhook、執行驗證
"""
from playwright.async_api import Page


async def configure(page: Page, channel_id: str, webhook_url: str) -> None:
    url = f"https://developers.line.biz/console/channel/{channel_id}/messagingapi"
    await page.goto(url, wait_until="networkidle", timeout=30000)

    # ── 輸入 Webhook URL ─────────────────────────────────────────

    webhook_input = await page.wait_for_selector(
        'input[name="webhookUrl"], '
        'input[placeholder*="webhook"], '
        'input[placeholder*="Webhook URL"]',
        timeout=10000,
    )
    await webhook_input.fill(webhook_url)

    # 儲存
    await page.click(
        'button:has-text("Update"), button:has-text("Save")',
        timeout=10000,
    )
    await page.wait_for_load_state("networkidle")
    print(f">>> Webhook URL 已設定：{webhook_url}")

    # ── 啟用 Use webhook ─────────────────────────────────────────

    try:
        toggle = await page.wait_for_selector(
            '[data-testid="use-webhook-toggle"] input, '
            'input[name="useWebhook"]',
            timeout=5000,
        )
        if not await toggle.is_checked():
            await toggle.check()
            await page.wait_for_load_state("networkidle")
            print(">>> Use webhook 已啟用")
        else:
            print(">>> Use webhook 已是開啟狀態")
    except Exception:
        print(">>> （無法自動啟用 webhook toggle，請手動在 console 開啟）")

    # ── 驗證 Webhook ─────────────────────────────────────────────

    try:
        verify_btn = await page.wait_for_selector(
            'button:has-text("Verify")', timeout=5000
        )
        await verify_btn.click()
        await page.wait_for_load_state("networkidle")

        # 讀取驗證結果
        try:
            result = await page.wait_for_selector(
                '[class*="verifyResult"], [data-testid="verify-result"]',
                timeout=10000,
            )
            print(f">>> Webhook 驗證結果：{(await result.inner_text()).strip()}")
        except Exception:
            print(">>> Webhook 驗證請求已送出")
    except Exception:
        print(">>> （跳過 Webhook 驗證）")
