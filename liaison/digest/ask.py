"""ask.py — 專案推送待決問題給若可思

用法：
  uv run ask.py "NDA 用印的事你要怎麼處理？" --project ricky-contract
  uv run ask.py --file ASK_HUMAN.md --project thai-trip-2026

說明：
  各專案主動呼叫此 CLI，把需要 Logos 決定的問題推入 digest，
  由若可思在適當時機透過 LINE 問 Logos。
  不需要 scanner 主動去掃專案目錄。
"""
import os
import sys
import argparse
import re
from datetime import datetime, timezone

import psycopg

DB_URL       = os.environ.get("DIGEST_DB_URL", "")
AUTOMATA_DIR = os.environ.get("AUTOMATA_DIR", "/data/personal/automata")
UV_BIN       = os.environ.get("UV_BIN", "/home/logos/.local/bin/uv")


def _conn():
    return psycopg.connect(DB_URL)


def _parse_askhuman(path: str) -> list[str]:
    """從 ASK_HUMAN.md 取出未勾選項目（- [ ] ...）。"""
    items = []
    try:
        text = open(path).read()
        for line in text.splitlines():
            m = re.match(r"^\s*-\s*\[ \]\s*(?:\d{4}-\d{2}-\d{2}\s+)?(.+)", line)
            if m:
                items.append(m.group(1).strip())
    except FileNotFoundError:
        print(f"[ask] 找不到檔案：{path}", file=sys.stderr)
    return items


def _already_asked(conn, question: str, project: str) -> bool:
    """同專案同問題 7 天內已推過就跳過。"""
    row = conn.execute("""
        SELECT 1 FROM topic
        WHERE source_conversation_id = %s
          AND summary = %s
          AND resolved_at IS NULL
          AND first_seen_at > NOW() - INTERVAL '7 days'
        LIMIT 1
    """, (f"askhuman:{project}", question)).fetchone()
    return row is not None


def _push(conn, question: str, project: str, priority: str) -> str:
    """建立 topic + event，回傳 event_id。"""
    from embed import encode
    now = datetime.now(timezone.utc)
    embedding = encode(question)
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"

    topic_id = conn.execute("""
        INSERT INTO topic (summary, category, embedding, state,
                           first_seen_at, last_seen_at, settled_at,
                           source_conversation_id)
        VALUES (%s, 'task', %s::vector, 'judged', %s, %s, %s, %s)
        RETURNING id
    """, (question, vec_str, now, now, now, f"askhuman:{project}")).fetchone()[0]

    event_id = conn.execute("""
        INSERT INTO event (topic_id, summary, category, priority, occurred_at)
        VALUES (%s, %s, 'task', %s, %s)
        RETURNING id
    """, (topic_id, question, priority, now)).fetchone()[0]

    conn.commit()
    return str(event_id)


def _alert_ruocosi(question: str):
    import subprocess
    try:
        subprocess.Popen([
            "direnv", "exec", AUTOMATA_DIR,
            UV_BIN, "run", "--directory", AUTOMATA_DIR,
            "main.py", "--alert", question,
        ])
    except Exception as e:
        print(f"[ask] 通知若可思失敗：{e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="推送待決問題給若可思")
    ap.add_argument("question", nargs="?", help="問題內容")
    ap.add_argument("--file", "-f", help="從 ASK_HUMAN.md 批次推送")
    ap.add_argument("--project", "-p", required=True, help="專案名稱（用於去重）")
    ap.add_argument("--priority", default="high",
                    choices=["critical", "high", "normal"],
                    help="優先度（預設 high）")
    ap.add_argument("--alert", action="store_true",
                    help="立即通知若可思（預設等若可思下次主動觸發）")
    args = ap.parse_args()

    if not args.question and not args.file:
        ap.print_help()
        sys.exit(1)

    questions = []
    if args.file:
        questions = _parse_askhuman(args.file)
        if not questions:
            print("[ask] 沒有找到未勾選項目")
            return
    else:
        questions = [args.question]

    with _conn() as conn:
        pushed = skipped = 0
        for q in questions:
            if _already_asked(conn, q, args.project):
                print(f"[ask] 跳過（7 天內已推）：{q[:50]}")
                skipped += 1
                continue
            event_id = _push(conn, q, args.project, args.priority)
            print(f"[ask] ✓ {q[:60]}  →  event {event_id[:8]}…")
            pushed += 1
            if args.alert or args.priority == "critical":
                _alert_ruocosi(q)

    print(f"[ask] 完成：推送 {pushed}，跳過 {skipped}")


if __name__ == "__main__":
    main()
