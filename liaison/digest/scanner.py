"""scanner.py — 掃描 liaison-channel 新訊息，分類後存入 digest DB

用法：
  uv run scanner.py          # 單次掃描
  uv run scanner.py --watch  # 持續輪詢（每 SCAN_INTERVAL_MINUTES 分鐘）
"""
import os
import sys
import time
import json
import argparse
import httpx
import psycopg
from datetime import datetime, timezone

# ── 設定（從 .env 讀，direnv 注入）─────────────────────────────────

CHANNEL_API          = os.environ.get("CHANNEL_API", "http://localhost:8080")
DB_URL               = os.environ.get("DIGEST_DB_URL", "")
GEMINI_API_KEY       = os.environ.get("GEMINI_API_KEY", "")
SCAN_INTERVAL        = int(os.environ.get("SCAN_INTERVAL_MINUTES", "10"))
LOOKBACK_MINUTES     = int(os.environ.get("LOOKBACK_MINUTES", "60"))

# 這些 external_id 是 bot/AI 發出的，不列入分類
BOT_SENDER_IDS = {
    "U208cdb619ae970a3e5f1f6f368339e27",  # 若可思 LINE OA
}


# ── DB ────────────────────────────────────────────────────────────

def _conn():
    return psycopg.connect(DB_URL)


def _already_processed(conn, external_message_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM event_message WHERE external_message_id = %s LIMIT 1",
        (external_message_id,)
    ).fetchone()
    return row is not None


def _insert_event(conn, msg: dict, category: str, priority: str, summary: str):
    event_id = conn.execute("""
        INSERT INTO event (summary, category, priority, occurred_at, source_conversation_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        summary, category, priority,
        datetime.fromtimestamp(msg["created_at"] / 1000, tz=timezone.utc),
        msg.get("conversation_id"),
    )).fetchone()[0]

    conn.execute(
        "INSERT INTO event_message (event_id, external_message_id) VALUES (%s, %s)",
        (event_id, msg["external_id"] or msg["id"]),
    )
    conn.commit()


# ── Claude 分類 ───────────────────────────────────────────────────

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "/home/logos/.local/bin/claude")

CLASSIFY_PROMPT = """你是訊息分類助理。根據以下訊息內容，輸出 JSON：
{
  "category": "task|question|info|social|alert|unknown",
  "priority": "critical|high|normal|low",
  "summary": "20字內的中文摘要，說明這則訊息的核心內容"
}

分類規則：
- task: 需要 Logos 執行某件事
- question: 對方在等 Logos 回覆
- info: 純資訊，不需立即行動
- social: 閒聊、打招呼
- alert: 警示、異常、緊急
- unknown: 無法判斷

只輸出 JSON，不加其他說明。"""


def _classify(sender_name: str, text: str) -> tuple[str, str, str]:
    """回傳 (category, priority, summary)，失敗時回傳預設值。"""
    import subprocess
    prompt = f"{CLASSIFY_PROMPT}\n\n發送者：{sender_name}\n訊息：{text}"
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"[scanner] claude 回傳錯誤：{result.stderr[:100]}", file=sys.stderr)
            return "unknown", "normal", text[:20]
        raw = result.stdout.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return data["category"], data["priority"], data["summary"]
    except Exception as e:
        print(f"[scanner] 分類失敗：{e}", file=sys.stderr)
        return "unknown", "normal", text[:20]


# ── 即時通知 ──────────────────────────────────────────────────────

AUTOMATA_DIR = os.environ.get("AUTOMATA_DIR", "/data/personal/automata")
UV_BIN       = os.environ.get("UV_BIN", "/home/logos/.local/bin/uv")


def _alert_ruocosi(summary: str) -> None:
    """新 high/critical 事件：立即叫若可思通知 Logos 確認。"""
    import subprocess
    try:
        subprocess.Popen([
            "direnv", "exec", AUTOMATA_DIR,
            UV_BIN, "run", "--directory", AUTOMATA_DIR,
            "main.py", "--alert", summary,
        ])
        print(f"[scanner] 已通知若可思：{summary[:40]}")
    except Exception as e:
        print(f"[scanner] 通知若可思失敗：{e}", file=sys.stderr)


# ── 主掃描邏輯 ────────────────────────────────────────────────────

def scan_once():
    since_ts = int((time.time() - LOOKBACK_MINUTES * 60) * 1000)

    # 取所有 conversation
    try:
        convs = httpx.get(f"{CHANNEL_API}/conversations", timeout=10).json()
    except Exception as e:
        print(f"[scanner] 無法取得 conversations：{e}", file=sys.stderr)
        return

    processed = skipped = 0

    with _conn() as conn:
        for conv in convs:
            conv_id = conv["conversation_id"]
            channel = conv.get("channel", "")

            try:
                msgs = httpx.get(
                    f"{CHANNEL_API}/conversations/{conv_id}/messages",
                    params={"limit": 50},
                    timeout=10,
                ).json()
            except Exception as e:
                print(f"[scanner] {channel}/{conv_id[:8]} 讀取失敗：{e}", file=sys.stderr)
                continue

            for msg in msgs:
                if msg.get("created_at", 0) < since_ts:
                    continue
                if not msg.get("text"):
                    continue
                if msg.get("sender_external_id") in BOT_SENDER_IDS:
                    continue

                ext_id = msg.get("external_id") or msg["id"]
                if _already_processed(conn, ext_id):
                    skipped += 1
                    continue

                sender = msg.get("sender_name") or msg.get("sender_external_id", "unknown")
                category, priority, summary = _classify(sender, msg["text"])

                # social / low 不存入 DB
                if category == "social" and priority == "low":
                    skipped += 1
                    continue

                _insert_event(conn, msg, category, priority, summary)
                processed += 1
                print(f"[scanner] [{priority}][{category}] {summary[:40]}")

                if priority in ("high", "critical"):
                    _alert_ruocosi(summary)

    print(f"[scanner] 完成：新增 {processed}，跳過 {skipped}")


# ── 入口 ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true", help="持續輪詢")
    args = ap.parse_args()

    if args.watch:
        print(f"[scanner] 啟動，每 {SCAN_INTERVAL} 分鐘掃描一次")
        while True:
            scan_once()
            time.sleep(SCAN_INTERVAL * 60)
    else:
        scan_once()
