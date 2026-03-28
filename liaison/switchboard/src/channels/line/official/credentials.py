"""
credentials.py - LINE 官方帳號憑證管理

對外介面:
  save(secret, token)   儲存至 ~/.logos/secrets/line-official/
  load() -> dict        讀取 {channel_secret, channel_token}
  show()                印出現有憑證（遮蔽顯示）
"""
import os
from pathlib import Path


def _dir() -> Path:
    base = os.environ.get("LOGOS_ROOT", str(Path.home() / ".logos"))
    return Path(base) / "secrets" / "line-official"


def save(secret: str, token: str) -> None:
    d = _dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "channel-secret").write_text(secret.strip())
    (d / "channel-access-token").write_text(token.strip())
    print(f">>> 憑證已儲存至 {d}/")


def load() -> dict:
    d = _dir()

    def _r(name):
        p = d / name
        return p.read_text().strip() if p.exists() else ""

    return {
        "channel_secret": _r("channel-secret"),
        "channel_token":  _r("channel-access-token"),
    }


def show() -> None:
    c = load()

    def _mask(s):
        if not s:
            return "(未設定)"
        return (s[:6] + "..." + s[-4:]) if len(s) > 12 else "***"

    print(f"  Channel Secret      : {_mask(c['channel_secret'])}")
    print(f"  Channel Access Token: {_mask(c['channel_token'])}")
