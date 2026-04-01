"""test_gw_client.py - 測試 gw_client.py 的純邏輯（不需要 LINE 連線）"""

import json
import sys
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))
import gw_client


class TestFindExtPage(unittest.TestCase):
    def _make_ctx(self, urls):
        ctx = MagicMock()
        pages = []
        for url in urls:
            p = MagicMock()
            p.url = url
            pages.append(p)
        ctx.pages = pages
        return ctx, pages

    def test_finds_matching_page(self):
        ctx, pages = self._make_ctx([
            'chrome://newtab',
            f'chrome-extension://{gw_client.EXT_ID}/index.html',
            'https://example.com',
        ])
        self.assertIs(gw_client.find_ext_page(ctx), pages[1])

    def test_returns_first_match(self):
        ctx, pages = self._make_ctx([
            f'chrome-extension://{gw_client.EXT_ID}/a.html',
            f'chrome-extension://{gw_client.EXT_ID}/b.html',
        ])
        self.assertIs(gw_client.find_ext_page(ctx), pages[0])

    def test_raises_when_not_found(self):
        ctx, _ = self._make_ctx(['chrome://newtab', 'https://example.com'])
        with self.assertRaises(RuntimeError):
            gw_client.find_ext_page(ctx)

    def test_raises_on_empty_pages(self):
        ctx = MagicMock()
        ctx.pages = []
        with self.assertRaises(RuntimeError):
            gw_client.find_ext_page(ctx)


class TestComputeHmac(unittest.IsolatedAsyncioTestCase):
    """測試 compute_hmac 的 ltsm_not_ready retry 邏輯"""

    def _make_page(self, side_effect):
        page = MagicMock()
        page.evaluate = AsyncMock(side_effect=side_effect)
        return page

    async def test_success_immediately(self):
        page = self._make_page([{'hmac': 'abc123'}])
        result = await gw_client.compute_hmac(page, 'tok', '/path', '{}')
        self.assertEqual(result, 'abc123')

    async def test_retries_on_ltsm_not_ready(self):
        """ltsm_not_ready 兩次後成功"""
        side = [{'error': 'ltsm_not_ready'}, {'error': 'ltsm_not_ready'}, {'hmac': 'ok'}]
        page = self._make_page(side)
        with patch('gw_client.asyncio.sleep', new=AsyncMock()):
            result = await gw_client.compute_hmac(page, 'tok', '/path', '{}')
        self.assertEqual(result, 'ok')
        self.assertEqual(page.evaluate.call_count, 3)

    async def test_retries_on_no_iframe(self):
        """no iframe 也觸發 retry"""
        side = [{'error': 'no iframe'}, {'hmac': 'ok2'}]
        page = self._make_page(side)
        with patch('gw_client.asyncio.sleep', new=AsyncMock()):
            result = await gw_client.compute_hmac(page, 'tok', '/path', '{}')
        self.assertEqual(result, 'ok2')

    async def test_timeout_after_20_retries(self):
        """20 次都失敗 → 拋出 timeout 錯誤"""
        page = self._make_page([{'error': 'ltsm_not_ready'}] * 20)
        with patch('gw_client.asyncio.sleep', new=AsyncMock()):
            with self.assertRaises(RuntimeError) as ctx:
                await gw_client.compute_hmac(page, 'tok', '/path', '{}')
        self.assertIn('未就緒', str(ctx.exception))

    async def test_non_transient_error_raises_immediately(self):
        """非 not_ready 錯誤 → 立刻拋出，不重試"""
        page = self._make_page([{'error': 'timeout'}])
        with patch('gw_client.asyncio.sleep', new=AsyncMock()) as sl:
            with self.assertRaises(RuntimeError) as ctx:
                await gw_client.compute_hmac(page, 'tok', '/path', '{}')
        self.assertIn('HMAC 計算失敗', str(ctx.exception))
        self.assertEqual(sl.call_count, 0)


class TestCallApi(unittest.TestCase):
    def _mock_urlopen(self, response_dict):
        resp = MagicMock()
        resp.read.return_value = json.dumps(response_dict).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_success_returns_parsed_json(self):
        with patch('urllib.request.urlopen', return_value=self._mock_urlopen({'code': 0, 'data': []})):
            result = gw_client.call_api('/test', {'k': 'v'}, 'token', 'hmac')
        self.assertEqual(result['code'], 0)
        self.assertEqual(result['data'], [])

    def test_http_error_returns_error_dict(self):
        err = urllib.error.HTTPError('url', 403, 'Forbidden', {}, BytesIO(b'auth error'))
        with patch('urllib.request.urlopen', side_effect=err):
            result = gw_client.call_api('/test', {}, 'token', 'hmac')
        self.assertEqual(result['_error'], 403)
        self.assertIn('auth error', result['_body'])

    def test_request_includes_required_headers(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured['headers'] = dict(req.headers)
            return self._mock_urlopen({'code': 0})

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            gw_client.call_api('/test', {}, 'mytoken', 'myhmac')

        headers = {k.lower(): v for k, v in captured['headers'].items()}
        self.assertEqual(headers.get('x-line-access'), 'mytoken')
        self.assertEqual(headers.get('x-hmac'), 'myhmac')


if __name__ == '__main__':
    unittest.main()
