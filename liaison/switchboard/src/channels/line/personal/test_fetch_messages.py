"""test_fetch_messages.py - 測試 fetch_messages.py 的純邏輯（不需要 LINE 連線）"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent))
import fetch_messages


class TestParseArgs(unittest.TestCase):
    def _parse(self, argv):
        with patch('sys.argv', ['fetch_messages.py'] + argv):
            return fetch_messages.parse_args()

    def test_defaults(self):
        args = self._parse([])
        self.assertEqual(args.count, 50)
        self.assertIsNone(args.chat)
        self.assertEqual(args.output.name, 'messages.json')

    def test_custom_count(self):
        args = self._parse(['--count', '200'])
        self.assertEqual(args.count, 200)

    def test_chat_filter(self):
        args = self._parse(['--chat', 'Cabc123'])
        self.assertEqual(args.chat, 'Cabc123')

    def test_custom_output(self):
        args = self._parse(['--output', '/tmp/out.json'])
        self.assertEqual(args.output, Path('/tmp/out.json'))


class TestFetchChatMessages(unittest.IsolatedAsyncioTestCase):
    """測試 fetch_chat_messages 的 pagination 邏輯"""

    def _make_msgs(self, ids_times):
        return [{'id': str(i), 'createdTime': t} for i, t in ids_times]

    async def test_returns_empty_when_no_recent(self):
        page = object()
        with patch('fetch_messages._get_recent', AsyncMock(return_value=[])):
            result = await fetch_messages.fetch_chat_messages(page, 'tok', 'Cmid', 50)
        self.assertEqual(result, [])

    async def test_returns_recent_without_pagination_if_few(self):
        msgs = self._make_msgs([(1, 1000), (2, 2000)])
        with patch('fetch_messages._get_recent', AsyncMock(return_value=msgs)), \
             patch('fetch_messages._get_previous', AsyncMock(return_value=[])) as prev:
            result = await fetch_messages.fetch_chat_messages(object(), 'tok', 'Cmid', 50)
        self.assertEqual(result, msgs)
        prev.assert_not_called()  # count=2 < page_size=50，不 paginate

    async def test_paginates_when_full_page(self):
        # First page: 50 msgs (full)
        page1 = self._make_msgs([(i, i * 100) for i in range(51, 101)])  # 50 msgs
        # Previous page: 10 msgs (partial → stop)
        page2 = self._make_msgs([(i, i * 100) for i in range(41, 51)])   # 10 msgs

        with patch('fetch_messages._get_recent', AsyncMock(return_value=page1)), \
             patch('fetch_messages._get_previous', AsyncMock(return_value=page2)):
            result = await fetch_messages.fetch_chat_messages(object(), 'tok', 'Cmid', 50)

        self.assertEqual(len(result), 60)
        # page2 prepended before page1
        self.assertEqual(result[:10], page2)
        self.assertEqual(result[10:], page1)

    async def test_deduplicates_oldest_msg_from_previous(self):
        """_get_previous 的結果不應包含 oldest 那筆（重複過濾）"""
        oldest = {'id': '51', 'createdTime': 51}
        page1 = [oldest] + self._make_msgs([(i, i * 10) for i in range(52, 101)])
        # _get_previous 傳回含有 oldest 的清單
        page2_raw = self._make_msgs([(i, i * 10) for i in range(41, 53)])  # includes 51, 52

        with patch('fetch_messages._get_recent', AsyncMock(return_value=page1)), \
             patch('fetch_messages._get_previous', AsyncMock(return_value=page2_raw)):
            result = await fetch_messages.fetch_chat_messages(object(), 'tok', 'Cmid', 50)

        ids = [m['id'] for m in result]
        self.assertEqual(ids.count('51'), 1)  # 不重複

    async def test_stops_after_max_three_extra_pages(self):
        # 每次 _get_previous 回傳 50 筆全新的訊息，確保 dedup 後仍為滿頁
        # 這樣 loop 會跑滿 3 次才停
        call_count = {'n': 0}
        async def next_page(*args, **kwargs):
            base = (call_count['n'] + 1) * 1000
            call_count['n'] += 1
            return [{'id': str(base + i), 'createdTime': base + i} for i in range(50)]

        initial = self._make_msgs([(i, i) for i in range(50)])
        with patch('fetch_messages._get_recent', AsyncMock(return_value=initial)), \
             patch('fetch_messages._get_previous', side_effect=next_page):
            await fetch_messages.fetch_chat_messages(object(), 'tok', 'Cmid', 50)

        self.assertEqual(call_count['n'], 3)  # 最多 3 次


if __name__ == '__main__':
    unittest.main()
