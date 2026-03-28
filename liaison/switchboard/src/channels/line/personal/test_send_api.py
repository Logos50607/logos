"""test_send_api.py - 測試 send_api.py 的 retry 邏輯（不需要 LINE 連線）"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))
import send_api


class TestSendE2eeText(unittest.IsolatedAsyncioTestCase):
    """測試 send_e2ee_text 的 key rotation retry 邏輯"""

    def _base_patches(self, do_send_mock):
        return patch.multiple(
            'send_api',
            get_access_token=AsyncMock(return_value='tok'),
            get_my_info=AsyncMock(return_value=('Umid123', 1001)),
            get_recipient_key=AsyncMock(return_value=(2002, 'pubkeyB64==')),
            _do_send=do_send_mock,
        )

    async def test_success_first_attempt(self):
        do_send = AsyncMock(return_value={'code': 0, '_seq': 42})
        with self._base_patches(do_send):
            result = await send_api.send_e2ee_text(MagicMock(), 'Uto', 'hello')
        self.assertEqual(result, {'ok': True, 'seq': 42})
        do_send.assert_called_once()

    async def test_code_83_returns_fatal_no_retry(self):
        do_send = AsyncMock(return_value={'code': 83, '_seq': 1})
        with self._base_patches(do_send):
            result = await send_api.send_e2ee_text(MagicMock(), 'Uto', 'hi')
        self.assertIn('error', result)
        self.assertIn('83', result['error'])
        do_send.assert_called_once()  # 不重試

    async def test_code_84_retries_and_succeeds(self):
        responses = [{'code': 84, '_seq': 1}, {'code': 0, '_seq': 99}]
        do_send = AsyncMock(side_effect=responses)
        with self._base_patches(do_send):
            result = await send_api.send_e2ee_text(MagicMock(), 'Uto', 'hi')
        self.assertEqual(result, {'ok': True, 'seq': 99})
        self.assertEqual(do_send.call_count, 2)

    async def test_code_82_retries_and_succeeds(self):
        responses = [{'code': 82, '_seq': 1}, {'code': 0, '_seq': 77}]
        do_send = AsyncMock(side_effect=responses)
        with self._base_patches(do_send):
            result = await send_api.send_e2ee_text(MagicMock(), 'Uto', 'hi')
        self.assertEqual(result, {'ok': True, 'seq': 77})

    async def test_receiver_key_refreshed_on_retry(self):
        """code 84 時應重新呼叫 get_recipient_key"""
        responses = [{'code': 84, '_seq': 1}, {'code': 0, '_seq': 5}]
        do_send = AsyncMock(side_effect=responses)
        fresh_key = AsyncMock(return_value=(9999, 'freshPubKey=='))
        with patch.multiple(
            'send_api',
            get_access_token=AsyncMock(return_value='tok'),
            get_my_info=AsyncMock(return_value=('Umid', 1001)),
            get_recipient_key=fresh_key,
            _do_send=do_send,
        ):
            await send_api.send_e2ee_text(MagicMock(), 'Uto', 'hi')
        # 初次 + retry 各呼叫一次
        self.assertEqual(fresh_key.call_count, 2)

    async def test_exhausts_all_retries(self):
        do_send = AsyncMock(return_value={'code': 84, '_seq': 1})
        with self._base_patches(do_send):
            result = await send_api.send_e2ee_text(MagicMock(), 'Uto', 'hi')
        self.assertIn('error', result)
        self.assertIn('重試', result['error'])
        self.assertEqual(do_send.call_count, 3)

    async def test_unknown_code_returns_error(self):
        do_send = AsyncMock(return_value={'code': 500, '_seq': 1})
        with self._base_patches(do_send):
            result = await send_api.send_e2ee_text(MagicMock(), 'Uto', 'hi')
        self.assertIn('error', result)
        self.assertIn('500', result['error'])
        do_send.assert_called_once()  # 不重試


if __name__ == '__main__':
    unittest.main()
