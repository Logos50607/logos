# /// script
# dependencies = ["playwright", "pillow", "zxing-cpp", "qrcode[pil]"]
# ///
"""
rename.py - 修改 LINE 官方帳號顯示名稱

用法：
  uv run rename.py --name "新名稱" [--oa-id @864unwcu]

流程：
  1. 前往 page.line.biz 取得帳號 page ID
  2. PUT /api/cms/v2/account-page/{pageId}/display-name
  3. 點擊 modal 確認公開（7天內不可再改）

auth 從 session-state.json 讀取（先跑 login.py）
"""
import argparse, asyncio, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import login


async def rename_oa(oa_id: str, new_name: str) -> None:
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
            viewport={"width": 1280, "height": 900},
        )

        # 攔截 PUT display-name 的回應
        result: dict = {}
        async def _on_resp(resp):
            if "display-name" in resp.url and resp.request.method == "PUT":
                result["status"] = resp.status
                result["body"]   = await resp.text()
        ctx.on("response", _on_resp)

        page = await ctx.new_page()
        print(f">>> 前往 page.line.biz ({oa_id})...")
        await page.goto(f"https://page.line.biz/account/{oa_id}",
                        wait_until="networkidle", timeout=20000)
        await asyncio.sleep(2)

        # 點擊帳號名稱旁的編輯鈕
        await page.click('button[aria-label="編輯"]')
        await asyncio.sleep(0.5)

        el = await page.wait_for_selector('input[type="text"]', timeout=3000)
        old_name = await el.input_value()
        print(f">>> 目前名稱：{old_name!r}  →  {new_name!r}")

        await el.click()
        await page.keyboard.press("Control+a")
        await el.fill(new_name)
        await asyncio.sleep(0.3)
        await page.click('button:has-text("確定")')
        await asyncio.sleep(1)

        # 點擊 modal 的「公開」確認（7天鎖）
        await page.evaluate("""() => {
            const modal = document.querySelector('.modal.show, [role="dialog"]');
            if (modal) {
                const btn = modal.querySelector('.btn-primary');
                if (btn) btn.click();
            }
        }""")
        await asyncio.sleep(3)

        if result.get("status") == 200:
            print(f">>> 改名成功：{new_name}")
        else:
            raise RuntimeError(
                f"改名失敗 HTTP {result.get('status', '?')}: {result.get('body', '')[:200]}"
            )

        await browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="修改 LINE OA 顯示名稱")
    ap.add_argument("--name",   required=True, help="新名稱")
    ap.add_argument("--oa-id",  default="@864unwcu", help="OA ID（預設 @864unwcu）")
    args = ap.parse_args()
    asyncio.run(rename_oa(args.oa_id, args.name))
