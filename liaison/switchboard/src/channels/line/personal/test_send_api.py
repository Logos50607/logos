"""test_send_api.py - 測試 send_api.py 的 retry 邏輯（不需要 LINE 連線）"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))
import send_api


_STORE_OK = json.dumps({'exportedKeyMap': {'2705364': 'pubkeydata=='}})


class TestGetMyInfo(unittest.IsolatedAsyncioTestCase):
    """測試 get_my_info 的 ltsm_not_ready retry 邏輯"""

    def _make_page(self, evaluate_side_effect):
        page = MagicMock()
        page.evaluate = AsyncMock(side_effect=evaluate_side_effect)
        return page

    async def test_success_immediately(self):
        """sandbox 立刻就緒 → 回傳 (mid, key_id)"""
        page = self._make_page([
            'Umid123',                          # localStorage key 查詢
            'enc_data',                          # localStorage.getItem
            {'ok': _STORE_OK},                   # decrypt_with_storage_key
        ])
        mid, key_id = await send_api.get_my_info(page)
        self.assertEqual(mid, 'Umid123')
        self.assertEqual(key_id, 2705364)

    async def test_ltsm_not_ready_retries_then_succeeds(self):
        """ltsm_not_ready 兩次後成功 → 共呼叫 sandbox 3 次"""
        not_ready = {'error': 'Error: ltsm_not_ready'}
        page = self._make_page([
            'Umid123', 'enc_data',
            not_ready, not_ready, {'ok': _STORE_OK},
        ])
        with patch('send_api.asyncio.sleep', new=AsyncMock()):
            mid, key_id = await send_api.get_my_info(page)
        self.assertEqual(mid, 'Umid123')
        self.assertEqual(key_id, 2705364)
        self.assertEqual(page.evaluate.call_count, 5)  # 2 + 3 sandbox calls

    async def test_ltsm_not_ready_timeout(self):
        """20 次都 ltsm_not_ready → 拋出 timeout 錯誤"""
        not_ready = {'error': 'Error: ltsm_not_ready'}
        page = self._make_page(['Umid123', 'enc_data'] + [not_ready] * 20)
        with patch('send_api.asyncio.sleep', new=AsyncMock()):
            with self.assertRaises(RuntimeError) as ctx:
                await send_api.get_my_info(page)
        self.assertIn('未就緒', str(ctx.exception))

    async def test_other_error_raises_immediately(self):
        """非 ltsm_not_ready 的錯誤 → 立刻拋出，不重試"""
        page = self._make_page([
            'Umid123', 'enc_data',
            {'error': 'Error: unknown_failure'},
        ])
        with patch('send_api.asyncio.sleep', new=AsyncMock()) as mock_sleep:
            with self.assertRaises(RuntimeError) as ctx:
                await send_api.get_my_info(page)
        self.assertIn('decrypt storage 失敗', str(ctx.exception))
        self.assertEqual(page.evaluate.call_count, 3)  # 不重試
        self.assertEqual(mock_sleep.call_count, 0)      # 沒有等待

    async def test_returns_max_key_id(self):
        """多個 key 時應回傳最大的"""
        store = json.dumps({'exportedKeyMap': {'2705363': 'a', '2705364': 'b', '9999999': 'c'}})
        page = self._make_page(['Umid123', 'enc_data', {'ok': store}])
        _, key_id = await send_api.get_my_info(page)
        self.assertEqual(key_id, 9999999)

    async def test_no_mid_raises(self):
        """找不到 lcs_secure_* → 拋出登入錯誤"""
        page = self._make_page([None])
        with self.assertRaises(RuntimeError) as ctx:
            await send_api.get_my_info(page)
        self.assertIn('登入', str(ctx.exception))


class TestSendE2eeGroup(unittest.IsolatedAsyncioTestCase):
    """測試群組發送（send_e2ee_group_text）"""

    def _group_patches(self, members, do_send_mock):
        return patch.multiple(
            'send_api',
            get_access_token=AsyncMock(return_value='tok'),
            get_my_info=AsyncMock(return_value=('Ume', 1001)),
            _group_members_from_history=MagicMock(return_value=members),
            get_recipient_key=AsyncMock(return_value=(2002, 'pub==')),
            _do_send=do_send_mock,
        )

    async def test_group_routes_from_send_e2ee_text(self):
        """to 不是 U... 應自動走群組路徑"""
        do_send = AsyncMock(return_value={'code': 0, '_seq': 1})
        with self._group_patches(['Umember1'], do_send):
            result = await send_api.send_e2ee_text(MagicMock(), 'Cgroup123', 'hi')
        self.assertIn('ok', result)

    async def test_group_sends_one_per_member(self):
        """每個成員各送一份"""
        do_send = AsyncMock(return_value={'code': 0, '_seq': 7})
        with self._group_patches(['Umember1', 'Umember2'], do_send):
            result = await send_api.send_e2ee_group_text(MagicMock(), 'Cgroup', 'hi')
        self.assertEqual(result, {'ok': True, 'seq': 7})
        self.assertEqual(do_send.call_count, 2)

    async def test_group_uses_to_type_2(self):
        """群組訊息的 to_type 必須是 2"""
        do_send = AsyncMock(return_value={'code': 0, '_seq': 1})
        with self._group_patches(['Umember1'], do_send):
            await send_api.send_e2ee_group_text(MagicMock(), 'Cgroup', 'hi')
        _, kwargs = do_send.call_args
        self.assertEqual(kwargs.get('to_type'), 2)

    async def test_group_no_members_returns_error(self):
        """找不到成員 → 回傳 error"""
        do_send = AsyncMock(return_value={'code': 0, '_seq': 1})
        with self._group_patches([], do_send):
            result = await send_api.send_e2ee_group_text(MagicMock(), 'Cgroup', 'hi')
        self.assertIn('error', result)
        do_send.assert_not_called()

    async def test_group_continues_on_key_fetch_failure(self):
        """某成員公鑰取得失敗 → 跳過繼續送其他人"""
        do_send = AsyncMock(return_value={'code': 0, '_seq': 5})
        get_key = AsyncMock(side_effect=[Exception('not found'), (3003, 'pub2==')])
        with patch.multiple('send_api',
                            get_access_token=AsyncMock(return_value='tok'),
                            get_my_info=AsyncMock(return_value=('Ume', 1001)),
                            _group_members_from_history=MagicMock(return_value=['Ufail', 'Uok']),
                            get_recipient_key=get_key,
                            _do_send=do_send):
            result = await send_api.send_e2ee_group_text(MagicMock(), 'Cgroup', 'hi')
        self.assertEqual(result, {'ok': True, 'seq': 5})
        self.assertEqual(do_send.call_count, 1)  # 只送給成功的那個


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
        self.assertEqual(do_send.call_count, 2)

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
        self.assertEqual(fresh_key.call_count, 2)  # 初次 + retry 各呼叫一次
        self.assertEqual(do_send.call_count, 2)    # 確認確實重試了一次

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


class TestDecryptE2eeMessage(unittest.IsolatedAsyncioTestCase):
    """測試 decrypt_e2ee_message 的 _load_my_key 失敗行為"""

    def _make_msg(self, s_key=2705364, r_key=9999, from_mid='Usender', to_mid='Ume'):
        import base64, struct
        def enc(n): return base64.b64encode(struct.pack('>I', n)).decode()
        # chunks: [iv, cipher, seqkey, senderKey, receiverKey]
        return {
            'id': 'msgid1',
            'from': from_mid,
            'to': to_mid,
            'contentType': 0,
            'chunks': ['aaaaaa==', 'cipherdata==', 'seqkey==', enc(s_key), enc(r_key)],
        }

    async def test_load_my_key_failure_does_not_set_decrypt_skip(self):
        """_load_my_key 失敗時不設 _decrypt_skip（可能是 LTSM 暫時未就緒）"""
        msg = self._make_msg(s_key=2000, r_key=2705364, from_mid='Usender', to_mid='Ume')
        ltsm_cache: dict = {}
        chan_cache: dict = {}
        pub_store: dict = {'2000': 'senderPub=='}

        with patch('send_api._load_my_key', new=AsyncMock(side_effect=RuntimeError('key not found in first 50 slots'))):
            result = await send_api.decrypt_e2ee_message(
                MagicMock(), msg, 'Ume', 'tok',
                ltsm_cache, chan_cache, pub_store,
            )
        self.assertIsNone(result)
        self.assertNotIn('_decrypt_skip', msg)  # 不應設永久 skip

    async def test_load_my_key_failure_sets_session_sentinel(self):
        """_load_my_key 失敗時在 ltsm_cache 設 -1 sentinel，避免同 session 重複掃描"""
        msg = self._make_msg(s_key=2000, r_key=2705364, from_mid='Usender', to_mid='Ume')
        ltsm_cache: dict = {}
        chan_cache: dict = {}
        pub_store: dict = {'2000': 'senderPub=='}

        with patch('send_api._load_my_key', new=AsyncMock(side_effect=RuntimeError('scan failed'))) as mock_load:
            # 第一次呼叫 → 失敗，設 sentinel
            await send_api.decrypt_e2ee_message(
                MagicMock(), msg, 'Ume', 'tok', ltsm_cache, chan_cache, pub_store,
            )
            self.assertEqual(ltsm_cache[2705364], -1)
            self.assertEqual(mock_load.call_count, 1)

            # 第二次呼叫同一 key → sentinel 命中，不再掃描
            msg2 = self._make_msg(s_key=2000, r_key=2705364, from_mid='Usender', to_mid='Ume')
            await send_api.decrypt_e2ee_message(
                MagicMock(), msg2, 'Ume', 'tok', ltsm_cache, chan_cache, pub_store,
            )
            self.assertEqual(mock_load.call_count, 1)  # 沒有再呼叫

    async def test_auth_failure_still_sets_decrypt_skip(self):
        """e2eechannel_decrypt 的 authentication failure → 仍設 _decrypt_skip"""
        msg = self._make_msg(s_key=2000, r_key=2705364, from_mid='Usender', to_mid='Ume')
        ltsm_cache: dict = {2705364: 99}  # 私鑰已在 cache
        chan_cache: dict = {}
        pub_store: dict = {'2000': 'senderPub=='}

        with patch('send_api._load_my_key', new=AsyncMock(return_value=99)), \
             patch('send_api.make_decrypt_channel', new=AsyncMock(return_value=42)), \
             patch('send_api.decrypt_e2ee_chunks', new=AsyncMock(side_effect=RuntimeError('data authentication failure'))):
            result = await send_api.decrypt_e2ee_message(
                MagicMock(), msg, 'Ume', 'tok', ltsm_cache, chan_cache, pub_store,
            )
        self.assertIsNone(result)
        self.assertTrue(msg.get('_decrypt_skip'))  # 加密資料損壞，永久 skip


if __name__ == '__main__':
    unittest.main()
