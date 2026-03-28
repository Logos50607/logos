"""test_gw_client.py - 測試 gw_client.py 的純邏輯（不需要 LINE 連線）"""

import json
import sys
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

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
