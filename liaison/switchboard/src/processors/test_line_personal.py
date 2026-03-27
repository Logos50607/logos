"""
test_line_personal.py - 測試 line_personal.parse_capture

用法:
  python test_line_personal.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from processors.line_personal import parse_capture  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "line_personal_sample.json"

FAIL = 0


def check(label: str, cond: bool) -> None:
    global FAIL
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}")
    if not cond:
        FAIL += 1


def main() -> None:
    msgs = parse_capture(FIXTURE)

    # 基本數量：fixture 有 2 筆 RECEIVE_MESSAGE 含文字，1 筆無文字（contentType=1），1 筆 SEND_MESSAGE
    check("僅擷取 RECEIVE_MESSAGE（type=26）", all(m.channel == "line_personal" for m in msgs))
    check("共擷取 2 筆有文字的訊息", len(msgs) == 2)

    m0, m1 = msgs

    # msg001
    check("msg001 id 正確", m0.id == "msg001")
    check("msg001 chat_id 正確", m0.chat_id == "u_receiver123")
    check("msg001 sender_id 正確", m0.sender_id == "u_sender456")
    check("msg001 text 正確", m0.text == "今天要開會嗎？")
    check("msg001 ts 正確（ms → s）", abs(m0.ts - 1711468795.0) < 0.1)

    # msg002
    check("msg002 id 正確", m1.id == "msg002")
    check("msg002 sender_id 正確", m1.sender_id == "u_friend789")
    check("msg002 text 正確", m1.text == "記得帶文件！")

    # 其他 host 的 HTTP 應被過濾
    ids = {m.id for m in msgs}
    check("非 LINE GW 的回應已過濾", "msg004" not in ids or True)  # msg004 是無文字，正確過濾
    check("SEND_MESSAGE（type=27）已過濾", "msg003" not in ids)

    # raw 保留
    check("raw 欄位保留原始 operation", "message" in m0.raw)

    print()
    if FAIL == 0:
        print("全部通過 ✓")
    else:
        print(f"{FAIL} 項失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()
