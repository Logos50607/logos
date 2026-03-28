"""
test_credentials.py - credentials 模組單元測試

執行：
  uv run test_credentials.py
"""
import os, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import credentials


def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["LOGOS_ROOT"] = tmp

        # 確認初始狀態為空
        c = credentials.load()
        assert c["channel_secret"] == "", f"初始應為空，但得到：{c['channel_secret']}"
        assert c["channel_token"]  == "", f"初始應為空，但得到：{c['channel_token']}"

        # 儲存
        credentials.save("test-secret-abc", "test-token-xyz")

        # 讀取並驗證
        c = credentials.load()
        assert c["channel_secret"] == "test-secret-abc", f"Secret 不符：{c['channel_secret']}"
        assert c["channel_token"]  == "test-token-xyz",  f"Token 不符：{c['channel_token']}"

        # 覆寫
        credentials.save("new-secret", "new-token")
        c = credentials.load()
        assert c["channel_secret"] == "new-secret"
        assert c["channel_token"]  == "new-token"

    print("✓ test_save_and_load 通過")


def test_mask_display(capsys=None):
    """show() 不應輸出完整憑證"""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["LOGOS_ROOT"] = tmp
        credentials.save("abcdefghijklmn", "ZYXWVUTSRQPONM")

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            credentials.show()
        output = buf.getvalue()

        assert "abcdefghijklmn" not in output, "完整 secret 不應出現在輸出中"
        assert "ZYXWVUTSRQPONM" not in output, "完整 token 不應出現在輸出中"
        assert "..." in output, "應有遮蔽符號"

    print("✓ test_mask_display 通過")


if __name__ == "__main__":
    test_save_and_load()
    test_mask_display()
    print("\n所有測試通過 ✓")
