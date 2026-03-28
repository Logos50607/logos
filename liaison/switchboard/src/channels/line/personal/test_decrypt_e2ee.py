"""test_decrypt_e2ee.py - 測試 decrypt_e2ee.py 的純邏輯（不需要 LINE 連線）"""

import base64
import json
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))
import decrypt_e2ee


# ── 測試工具 ──────────────────────────────────────────────────────

def _make_message(sender_key_id: int, receiver_key_id: int,
                  content_type: int = 0) -> dict:
    """建立測試用訊息 dict，chunks 使用固定值。"""
    iv        = b'\x01' * 16
    ciphertext = b'\x02' * 32
    seq_key_id = b'\x00' * 12
    skid_bytes = struct.pack('>I', sender_key_id)
    rkid_bytes = struct.pack('>I', receiver_key_id)
    return {
        'id': 'msg001',
        'from': 'Usender',
        'to':   'Ureceiver',
        'contentType': content_type,
        'chunks': [
            base64.b64encode(iv).decode(),
            base64.b64encode(ciphertext).decode(),
            base64.b64encode(seq_key_id).decode(),
            base64.b64encode(skid_bytes).decode(),
            base64.b64encode(rkid_bytes).decode(),
        ],
        'contentMetadata': {},
    }


# ── _parse_chunks ─────────────────────────────────────────────────

class TestParseChunks(unittest.TestCase):
    def test_parses_key_ids(self):
        msg = _make_message(0x00123456, 0x00654321)
        raw, sid, rid = decrypt_e2ee._parse_chunks(msg)
        self.assertEqual(sid, 0x00123456)
        self.assertEqual(rid, 0x00654321)

    def test_raw_length(self):
        msg = _make_message(1, 2)
        raw, _, _ = decrypt_e2ee._parse_chunks(msg)
        # IV(16) + seqKeyId(12) + ciphertext(32)
        self.assertEqual(len(raw), 60)

    def test_raw_order(self):
        """raw 開頭應是 IV，接著 seqKeyId。"""
        msg = _make_message(1, 2)
        raw, _, _ = decrypt_e2ee._parse_chunks(msg)
        self.assertEqual(raw[:16],  b'\x01' * 16)  # IV
        self.assertEqual(raw[16:28], b'\x00' * 12) # seqKeyId
        self.assertEqual(raw[28:],  b'\x02' * 32)  # ciphertext


# ── build_talk_meta（從 download_image 模組匯入）─────────────────

class TestBuildTalkMeta(unittest.TestCase):
    def _decode(self, meta: str) -> dict:
        padded = meta + '=' * (-len(meta) % 4)
        json_str = base64.urlsafe_b64decode(padded).decode('utf-8')
        return json.loads(json_str)

    def test_is_base64url(self):
        from download_image import build_talk_meta
        meta = build_talk_meta('12345')
        # Should not contain + or /
        self.assertNotIn('+', meta)
        self.assertNotIn('/', meta)

    def test_contains_message_key(self):
        from download_image import build_talk_meta
        meta = build_talk_meta('12345')
        decoded = self._decode(meta)
        self.assertIn('message', decoded)

    def test_message_id_in_thrift(self):
        from download_image import build_talk_meta
        meta = build_talk_meta('hello')
        decoded = self._decode(meta)
        thrift_bytes = base64.b64decode(decoded['message'])
        self.assertIn(b'hello', thrift_bytes)

    def test_different_ids_produce_different_metas(self):
        from download_image import build_talk_meta
        m1 = build_talk_meta('123')
        m2 = build_talk_meta('456')
        self.assertNotEqual(m1, m2)


# ── _derive_keys（從 download_image 模組匯入）───────────────────

class TestDeriveKeys(unittest.TestCase):
    def test_key_lengths(self):
        from download_image import _derive_keys
        import os
        km_b64 = base64.b64encode(os.urandom(32)).decode()
        enc_key, mac_key, nonce = _derive_keys(km_b64)
        self.assertEqual(len(enc_key), 32)
        self.assertEqual(len(mac_key), 32)
        self.assertEqual(len(nonce), 12)

    def test_deterministic(self):
        from download_image import _derive_keys
        km_b64 = base64.b64encode(b'\xAB' * 32).decode()
        r1 = _derive_keys(km_b64)
        r2 = _derive_keys(km_b64)
        self.assertEqual(r1, r2)

    def test_different_input_different_output(self):
        from download_image import _derive_keys
        k1 = _derive_keys(base64.b64encode(b'\x01' * 32).decode())
        k2 = _derive_keys(base64.b64encode(b'\x02' * 32).decode())
        self.assertNotEqual(k1[0], k2[0])


# ── _decrypt_image_bytes（從 download_image 模組匯入）───────────

class TestDecryptImageBytes(unittest.TestCase):
    def _make_encrypted(self, km_b64: str, plaintext: bytes) -> bytes:
        """用相同 km 加密，建立測試用的加密資料。"""
        import hashlib, hmac as hmac_lib, os
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from download_image import _derive_keys
        enc_key, mac_key, nonce = _derive_keys(km_b64)
        counter = bytes(nonce) + b'\x00\x00\x00\x00'
        cipher = Cipher(algorithms.AES(enc_key), modes.CTR(counter))
        enc = cipher.encryptor()
        ciphertext = enc.update(plaintext) + enc.finalize()
        mac = hmac_lib.new(mac_key, ciphertext, hashlib.sha256).digest()
        return ciphertext + mac

    def test_roundtrip(self):
        from download_image import _decrypt_image_bytes
        km_b64 = base64.b64encode(b'\xCC' * 32).decode()
        plaintext = b'\xFF\xD8\xFF' + b'\x00' * 100  # fake JPEG
        encrypted = self._make_encrypted(km_b64, plaintext)
        result = _decrypt_image_bytes(encrypted, km_b64)
        self.assertEqual(result, plaintext)

    def test_hmac_mismatch_raises(self):
        from download_image import _decrypt_image_bytes
        km_b64 = base64.b64encode(b'\xAA' * 32).decode()
        encrypted = self._make_encrypted(km_b64, b'hello')
        tampered = encrypted[:-1] + bytes([encrypted[-1] ^ 0xFF])
        with self.assertRaises(ValueError):
            _decrypt_image_bytes(tampered, km_b64)


# ── decrypt_chunks（integration mock）────────────────────────────

class TestDecryptChunks(unittest.IsolatedAsyncioTestCase):
    async def test_success_received_message(self):
        """接收到的訊息：chunks[4]=我的key(200)，chunks[3]=對方key(100)。"""
        # from=Usender(對方), to=Ureceiver(我)
        msg = _make_message(sender_key_id=100, receiver_key_id=200)
        plaintext_dict = {'text': 'hello world'}

        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock()

        fake_store = json.dumps({'exportedKeyMap': {'200': 'privkeyB64=='}})
        mock_page.evaluate.side_effect = [
            'Ureceiver',           # _get_my_mid: lcs_secure_ scan
            'encrypted_storage',   # localStorage.getItem('lcs_secure_Ureceiver')
            {'ok': fake_store},    # decrypt_with_storage_key
            {'ok': 999},           # e2eekey_load_key
            {'ok': 777},           # e2eekey_create_channel
            {'ok': base64.b64encode(json.dumps(plaintext_dict).encode()).decode()},
        ]

        with patch('decrypt_e2ee._get_sender_key',
                   AsyncMock(return_value=(100, 'pubkeyB64=='))):
            result = await decrypt_e2ee.decrypt_chunks(mock_page, 'tok', msg)

        self.assertEqual(result, plaintext_dict)

    async def test_success_sent_message(self):
        """我傳送的訊息：chunks[3]=我的key(100)，chunks[4]=對方key(200)。"""
        # from=Usender(我), to=Ureceiver(對方)
        msg = _make_message(sender_key_id=100, receiver_key_id=200)
        msg['from'], msg['to'] = 'Usender', 'Ureceiver'
        plaintext_dict = {'keyMaterial': 'km=='}

        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock()

        fake_store = json.dumps({'exportedKeyMap': {'100': 'myprivkeyB64=='}})
        mock_page.evaluate.side_effect = [
            'Usender',             # _get_my_mid
            'encrypted_storage',   # localStorage.getItem
            {'ok': fake_store},    # decrypt_with_storage_key (key 100)
            {'ok': 888},           # e2eekey_load_key
            {'ok': 555},           # e2eekey_create_channel
            {'ok': base64.b64encode(json.dumps(plaintext_dict).encode()).decode()},
        ]

        with patch('decrypt_e2ee._get_sender_key',
                   AsyncMock(return_value=(200, 'recipientPubKey=='))):
            result = await decrypt_e2ee.decrypt_chunks(mock_page, 'tok', msg)

        self.assertEqual(result, plaintext_dict)

    async def test_storage_decrypt_failure(self):
        msg = _make_message(1, 2)
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(side_effect=[
            'Ureceiver',     # _get_my_mid
            'enc_storage',   # localStorage.getItem
            {'error': 'bad key'},
        ])
        with patch('decrypt_e2ee._get_sender_key', AsyncMock(return_value=(1, 'pub=='))):
            with self.assertRaises(RuntimeError, msg='decrypt storage 失敗'):
                await decrypt_e2ee.decrypt_chunks(mock_page, 'tok', msg)


if __name__ == '__main__':
    unittest.main()
