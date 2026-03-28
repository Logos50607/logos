"""test_send_image.py - 測試 send_image.py 的純邏輯（不需要 LINE 連線）"""

import base64
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))
import send_image


# ── _generate_km ─────────────────────────────────────────────────

class TestGenerateKm(unittest.TestCase):
    def test_length(self):
        km_b64, km_bytes = send_image._generate_km()
        self.assertEqual(len(base64.b64decode(km_b64)), 32)
        self.assertEqual(len(km_bytes), 32)

    def test_randomness(self):
        km1, _ = send_image._generate_km()
        km2, _ = send_image._generate_km()
        self.assertNotEqual(km1, km2)


# ── _encrypt_image / decrypt roundtrip ───────────────────────────

class TestEncryptImage(unittest.TestCase):
    def _decrypt(self, enc_data: bytes, km_b64: str) -> bytes:
        from download_image import _decrypt_image_bytes
        return _decrypt_image_bytes(enc_data, km_b64)

    def test_roundtrip(self):
        plain = b'\xFF\xD8\xFF' + b'\x00' * 200
        km_b64, _ = send_image._generate_km()
        enc = send_image._encrypt_image(plain, km_b64)
        result = self._decrypt(enc, km_b64)
        self.assertEqual(result, plain)

    def test_encrypted_longer_than_plain(self):
        plain = b'hello image'
        km_b64, _ = send_image._generate_km()
        enc = send_image._encrypt_image(plain, km_b64)
        # +32 bytes HMAC
        self.assertEqual(len(enc), len(plain) + 32)

    def test_different_km_different_ciphertext(self):
        plain = b'same data'
        km1, _ = send_image._generate_km()
        km2, _ = send_image._generate_km()
        enc1 = send_image._encrypt_image(plain, km1)
        enc2 = send_image._encrypt_image(plain, km2)
        self.assertNotEqual(enc1[:len(plain)], enc2[:len(plain)])


# ── _build_send_body ─────────────────────────────────────────────

class TestBuildSendBody(unittest.TestCase):
    def test_basic_structure(self):
        body = send_image._build_send_body(
            seq_num=12345, to='Uto', my_mid='Ume',
            oid='test-oid', file_size=1000, chunks=['a', 'b']
        )
        self.assertEqual(body[0], 12345)
        msg = body[1]
        self.assertEqual(msg['contentType'], 1)
        self.assertEqual(msg['to'], 'Uto')
        self.assertEqual(msg['from'], 'Ume')
        self.assertEqual(msg['chunks'], ['a', 'b'])

    def test_content_metadata(self):
        body = send_image._build_send_body(
            seq_num=1, to='Uto', my_mid='Ume',
            oid='some-oid', file_size=5000, chunks=[]
        )
        meta = body[1]['contentMetadata']
        self.assertEqual(meta['SID'], 'emi')
        self.assertEqual(meta['OID'], 'some-oid')
        self.assertEqual(meta['e2eeVersion'], '2')
        self.assertEqual(meta['FILE_SIZE'], '5000')

    def test_has_content_false(self):
        body = send_image._build_send_body(1, 'Uto', 'Ume', 'oid', 100, [])
        self.assertFalse(body[1]['hasContent'])


# ── send_image（integration mock）────────────────────────────────

class TestSendImage(unittest.IsolatedAsyncioTestCase):
    async def test_success(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF' + b'\x00' * 100)
            tmp_path = Path(f.name)

        try:
            mock_page = MagicMock()
            mock_page.evaluate = AsyncMock()

            with patch.multiple(
                'send_image',
                get_access_token=AsyncMock(return_value='tok'),
                get_my_info=AsyncMock(return_value=('Ume', 1001)),
                get_recipient_key=AsyncMock(return_value=(2002, 'pubkeyB64==')),
                get_obs_token=AsyncMock(return_value='obs_tok'),
                encrypt_message=AsyncMock(return_value=['c1', 'c2', 'c3', 'c4', 'c5']),
                compute_hmac=AsyncMock(return_value='hmac=='),
                call_api=MagicMock(return_value={'code': 0}),
            ), patch.object(send_image, '_obs_upload', return_value='server-oid'), \
               patch.object(send_image, '_encrypt_image', return_value=b'enc'):
                result = await send_image.send_image(mock_page, 'Uto', tmp_path)

            self.assertTrue(result.get('ok'))
        finally:
            os.unlink(tmp_path)

    async def test_obs_upload_failure_propagates(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF')
            tmp_path = Path(f.name)

        try:
            with patch.multiple(
                'send_image',
                get_access_token=AsyncMock(return_value='tok'),
                get_my_info=AsyncMock(return_value=('Ume', 1001)),
                get_recipient_key=AsyncMock(return_value=(2002, 'pub==')),
                get_obs_token=AsyncMock(return_value='obs_tok'),
            ), patch.object(send_image, '_encrypt_image', return_value=b'enc'), \
               patch.object(send_image, '_obs_upload',
                             side_effect=RuntimeError("upload failed")):
                with self.assertRaises(RuntimeError):
                    await send_image.send_image(MagicMock(), 'Uto', tmp_path)
        finally:
            os.unlink(tmp_path)

    async def test_send_failure_returns_error(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF')
            tmp_path = Path(f.name)

        try:
            with patch.multiple(
                'send_image',
                get_access_token=AsyncMock(return_value='tok'),
                get_my_info=AsyncMock(return_value=('Ume', 1001)),
                get_recipient_key=AsyncMock(return_value=(2002, 'pub==')),
                get_obs_token=AsyncMock(return_value='obs_tok'),
                encrypt_message=AsyncMock(return_value=['c1', 'c2', 'c3', 'c4', 'c5']),
                compute_hmac=AsyncMock(return_value='hmac=='),
                call_api=MagicMock(return_value={'code': 999, 'message': 'fail'}),
            ), patch.object(send_image, '_encrypt_image', return_value=b'enc'), \
               patch.object(send_image, '_obs_upload', return_value='oid'):
                result = await send_image.send_image(MagicMock(), 'Uto', tmp_path)

            self.assertIn('error', result)
        finally:
            os.unlink(tmp_path)


if __name__ == '__main__':
    unittest.main()
