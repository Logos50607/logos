"""
console.py - LINE Developers Console 操作（Provider + Messaging API Channel）

對外介面:
  ensure_channel(page, provider, channel_name, email) -> dict
    建立或選取指定 provider 與 Messaging API channel，
    回傳 {channel_id, channel_secret, channel_token}

注意：本模組的 CSS selector 基於 LINE Developers Console 2024/2025 版面，
      若 UI 更新導致 selector 失效，請依實際 DOM 結構調整。
"""
import asyncio
from playwright.async_api import Page

_CONSOLE_URL = "https://developers.line.biz/console/"


async def ensure_channel(
    page: Page,
    provider: str,
    channel_name: str,
    email: str,
) -> dict:
    await _ensure_provider(page, provider)
    channel_id = await _ensure_messaging_api_channel(page, channel_name, email)
    return await _extract_credentials(page, channel_id)


# ── Provider ──────────────────────────────────────────────────────


async def _ensure_provider(page: Page, name: str) -> None:
    await page.goto(_CONSOLE_URL, wait_until="networkidle", timeout=30000)

    # 檢查是否已有此 provider
    try:
        await page.click(f'text="{name}"', timeout=5000)
        await page.wait_for_load_state("networkidle")
        print(f">>> 使用已有 Provider：{name}")
        return
    except Exception:
        pass

    # 建立新 provider
    print(f">>> 建立 Provider：{name}")
    await page.click('button:has-text("Create a provider"), a:has-text("Create a provider")',
                     timeout=10000)
    await page.fill(
        'input[name="providerName"], input[placeholder*="provider name"]', name
    )
    await page.click('button:has-text("Create")', timeout=10000)
    await page.wait_for_load_state("networkidle")
    print(f">>> Provider '{name}' 建立完成")


# ── Channel ───────────────────────────────────────────────────────


async def _ensure_messaging_api_channel(page: Page, name: str, email: str) -> str:
    """建立或選取 Messaging API channel，回傳 channel_id"""
    # 嘗試選取已有的同名 channel
    try:
        await page.click(f'text="{name}"', timeout=5000)
        await page.wait_for_load_state("networkidle")
        return _channel_id_from_url(page.url)
    except Exception:
        pass

    print(f">>> 建立 Messaging API Channel：{name}")
    await page.click('button:has-text("Create a channel"), a:has-text("Create a channel")',
                     timeout=10000)
    await page.click('text=Messaging API', timeout=10000)
    await page.wait_for_load_state("networkidle")

    # 填入必填欄位
    await page.fill('input[name="channelName"]', name, timeout=10000)
    await page.fill('input[name="email"], input[type="email"]', email, timeout=10000)

    # 選擇 Category（選第一個非預設選項，並等待 subcategory 更新）
    await page.select_option('select[name="categoryId"]', index=1)
    await asyncio.sleep(1)
    await page.select_option('select[name="subcategoryId"]', index=1)

    # 勾選所有同意條款 checkbox
    for cb in await page.query_selector_all('input[type="checkbox"]'):
        if not await cb.is_checked():
            await cb.check()

    await page.click('button:has-text("Create")', timeout=10000)
    await page.wait_for_load_state("networkidle")

    channel_id = _channel_id_from_url(page.url)
    print(f">>> Channel 建立完成，ID：{channel_id}")
    return channel_id


def _channel_id_from_url(url: str) -> str:
    parts = url.split("/")
    try:
        return parts[parts.index("channel") + 1]
    except (ValueError, IndexError):
        return ""


# ── 取得憑證 ──────────────────────────────────────────────────────


async def _extract_credentials(page: Page, channel_id: str) -> dict:
    base = f"https://developers.line.biz/console/channel/{channel_id}"

    # Channel Secret（Basic settings 頁）
    await page.goto(f"{base}/basic", wait_until="networkidle", timeout=30000)
    secret_el = await page.wait_for_selector(
        '[data-testid="channel-secret"] span, '
        'td:has-text("Channel secret") + td code, '
        '[class*="channelSecret"] code',
        timeout=10000,
    )
    channel_secret = (await secret_el.inner_text()).strip()

    # Channel Access Token（Messaging API 頁）
    await page.goto(f"{base}/messagingapi", wait_until="networkidle", timeout=30000)

    # 若尚未 Issue，點擊 Issue 按鈕
    try:
        btn = await page.wait_for_selector(
            'button:has-text("Issue"), button:has-text("Reissue")', timeout=5000
        )
        await btn.click()
        await page.wait_for_load_state("networkidle")
    except Exception:
        pass  # 已有 token

    token_el = await page.wait_for_selector(
        '[data-testid="channel-access-token"] code, '
        'td:has-text("Channel access token") + td code, '
        '[class*="accessToken"] code',
        timeout=10000,
    )
    channel_token = (await token_el.inner_text()).strip()

    return {
        "channel_id":     channel_id,
        "channel_secret": channel_secret,
        "channel_token":  channel_token,
    }
