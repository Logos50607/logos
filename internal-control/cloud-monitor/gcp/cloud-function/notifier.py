"""LINE 通知發送器。

環境變數未設定時 stub 至 stdout，OA ready 後填入即可。
"""
import json
import logging
import os
import urllib.request


def send(message: str) -> None:
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = os.environ.get("LINE_USER_ID", "")
    if not token or not user_id:
        logging.info("[LINE stub]\n%s", message)
        return
    _push(token, user_id, message)


def _push(token: str, user_id: str, message: str) -> None:
    payload = json.dumps({
        "to": user_id,
        "messages": [{"type": "text", "text": message}],
    }).encode()
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        logging.info("LINE push status: %s", resp.status)
