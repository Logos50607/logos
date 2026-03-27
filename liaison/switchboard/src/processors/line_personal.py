"""
line_personal.py - 解析 capture.py 產出的 LINE 個人帳號 captured.json

用法:
  python line_personal.py --input captured.json [--discover]

輸入: captured.json（capture.py 輸出，HTTP response 陣列）
輸出: list[Message]（stdout JSON）

LINE TalkService 操作 type 對照:
  26 = RECEIVE_MESSAGE（收到訊息）
  27 = SEND_MESSAGE（送出訊息）
  55 = SEND_CHAT_CHECKED（標記已讀，應不會出現）
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.schema import Message  # noqa: E402

RECEIVE_MSG_TYPE = 26
LINE_GW_HOST = "line-chrome-gw.line-apps.com"


def _op_to_message(op: dict) -> "Message | None":
    if op.get("type") != RECEIVE_MSG_TYPE:
        return None
    msg = op.get("message", {})
    text = msg.get("text") or ""
    if not text:
        return None
    ts_ms = msg.get("createdTime") or op.get("createdTime") or 0
    return Message(
        id=str(msg.get("id", "")),
        channel="line_personal",
        chat_id=str(msg.get("to", "")),
        sender_id=str(msg.get("from") or msg.get("_from", "")),
        text=text,
        ts=ts_ms / 1000,
        raw=op,
    )


def parse_capture(path: Path) -> list[Message]:
    """讀取 captured.json，回傳所有收到的文字訊息。"""
    entries = json.loads(path.read_text(encoding="utf-8"))
    messages: list[Message] = []
    for entry in entries:
        if entry.get("type") != "http":
            continue
        if LINE_GW_HOST not in entry.get("url", ""):
            continue
        body = entry.get("body", {})
        if not isinstance(body, dict):
            continue
        for op in body.get("operations", []):
            m = _op_to_message(op)
            if m is not None:
                messages.append(m)
    return messages


def _discover(path: Path) -> None:
    """印出 captured.json 中所有 operation type，協助了解資料結構。"""
    entries = json.loads(path.read_text(encoding="utf-8"))
    type_seen: dict[int, int] = {}
    for entry in entries:
        body = entry.get("body", {})
        if not isinstance(body, dict):
            continue
        for op in body.get("operations", []):
            t = op.get("type")
            type_seen[t] = type_seen.get(t, 0) + 1
    print(json.dumps({"operation_types": type_seen}, indent=2))


def _to_dict(m: Message) -> dict:
    return {k: v for k, v in m.__dict__.items() if k != "raw"}


def main() -> None:
    p = argparse.ArgumentParser(description="Parse LINE personal captured.json")
    p.add_argument("--input", type=Path, required=True, help="captured.json 路徑")
    p.add_argument("--discover", action="store_true", help="印出 operation type 統計")
    args = p.parse_args()

    if args.discover:
        _discover(args.input)
        return

    messages = parse_capture(args.input)
    print(json.dumps([_to_dict(m) for m in messages], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
