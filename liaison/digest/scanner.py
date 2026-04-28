"""scanner.py — 掃描 liaison-channel 新訊息，建立 topic，settled 後由 Claude judge 決定是否建 event

用法：
  uv run scanner.py          # 單次掃描 + settle check
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

# ── 設定 ──────────────────────────────────────────────────────────

CHANNEL_API      = os.environ.get("CHANNEL_API", "http://localhost:8080")
DB_URL           = os.environ.get("DIGEST_DB_URL", "")
SCAN_INTERVAL    = int(os.environ.get("SCAN_INTERVAL_MINUTES", "10"))
LOOKBACK_MINUTES = int(os.environ.get("LOOKBACK_MINUTES", "120"))
SETTLE_MINUTES   = int(os.environ.get("TOPIC_SETTLE_MINUTES", "15"))
CLAUDE_BIN       = os.environ.get("CLAUDE_BIN", "/home/logos/.local/bin/claude")
AUTOMATA_DIR     = os.environ.get("AUTOMATA_DIR", "/data/personal/automata")
UV_BIN           = os.environ.get("UV_BIN", "/home/logos/.local/bin/uv")

TOPIC_SIMILARITY_THRESHOLD = 0.85   # cosine similarity 門檻（跨對話去重）

BOT_SENDER_IDS = {
    "U208cdb619ae970a3e5f1f6f368339e27",  # 若可思 LINE OA
}


# ── DB ────────────────────────────────────────────────────────────

def _conn():
    return psycopg.connect(DB_URL)


def _already_processed(conn, external_message_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM topic_message WHERE external_message_id = %s LIMIT 1",
        (external_message_id,)
    ).fetchone()
    return row is not None


def _load_prompt(conn, name: str) -> str:
    row = conn.execute(
        "SELECT content FROM prompt WHERE name = %s", (name,)
    ).fetchone()
    if not row:
        raise ValueError(f"prompt '{name}' 不存在於 DB")
    return row[0]


def _load_identity_map(conn) -> dict[str, str]:
    """回傳 {nickname_lower: identity_id}，供名字對應。"""
    rows = conn.execute("""
        SELECT LOWER(ip.value), ip.identity_id
        FROM identity_property ip
        JOIN property_type pt ON pt.id = ip.property_type_id
        WHERE pt.name = 'nickname'
          AND ip.value NOT LIKE '(?) %'
    """).fetchall()
    return {name: uid for name, uid in rows}


# ── Embedding + Topic 去重 ─────────────────────────────────────────

def _find_topic_by_conversation(conn, conversation_id: str, category: str) -> str | None:
    """Layer 1：同對話有沒有 accumulating topic？"""
    row = conn.execute("""
        SELECT DISTINCT t.id FROM topic t
        JOIN topic_message tm ON tm.topic_id = t.id
        WHERE tm.conversation_id = %s
          AND t.category = %s
          AND t.state = 'accumulating'
        ORDER BY t.id LIMIT 1
    """, (conversation_id, category)).fetchone()
    return str(row[0]) if row else None


def _find_topic_by_embedding(conn, embedding: list[float], category: str) -> str | None:
    """Layer 2：向量相似度找跨對話的同類 topic。"""
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
    row = conn.execute("""
        SELECT id, 1 - (embedding <=> %s::vector) AS similarity
        FROM topic
        WHERE category = %s
          AND state = 'accumulating'
          AND embedding IS NOT NULL
          AND 1 - (embedding <=> %s::vector) >= %s
        ORDER BY embedding <=> %s::vector
        LIMIT 1
    """, (vec_str, category, vec_str, TOPIC_SIMILARITY_THRESHOLD, vec_str)).fetchone()
    return str(row[0]) if row else None


def _create_topic(conn, summary: str, category: str,
                  embedding: list[float], occurred_at: datetime) -> str:
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
    row = conn.execute("""
        INSERT INTO topic (summary, category, embedding, state, first_seen_at, last_seen_at)
        VALUES (%s, %s, %s::vector, 'accumulating', %s, %s)
        RETURNING id
    """, (summary, category, vec_str, occurred_at, occurred_at)).fetchone()
    conn.commit()
    return str(row[0])


def _attach_to_topic(conn, topic_id: str, msg: dict,
                     sender_name: str, summary: str, occurred_at: datetime):
    ext_id = msg.get("external_id") or msg["id"]
    conn.execute("""
        INSERT INTO topic_message (topic_id, external_message_id, conversation_id,
                                   sender_name, text, sent_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (topic_id, ext_id, msg.get("conversation_id"),
          sender_name, msg.get("text"), occurred_at))
    # 更新 topic 的 last_seen_at 與 summary
    conn.execute("""
        UPDATE topic SET last_seen_at = %s, summary = %s
        WHERE id = %s AND last_seen_at < %s
    """, (occurred_at, summary, topic_id, occurred_at))
    conn.commit()


# ── Identity 提取 ─────────────────────────────────────────────────

def _extract_identities(text: str, sender_name: str,
                        identity_map: dict[str, str]) -> list[tuple[str, str]]:
    """
    從訊息文字和發送者名稱找出相關 identity。
    回傳 [(identity_id, role), ...]，role: 'requester' | 'mentioned'
    """
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _match(name: str, role: str):
        key = name.lower()
        uid = identity_map.get(key)
        if uid and uid not in seen:
            results.append((uid, role))
            seen.add(uid)

    _match(sender_name, "requester")

    # 在訊息文字裡找 identity_map 的名字
    text_lower = text.lower()
    for nickname, uid in identity_map.items():
        if nickname in text_lower and uid not in seen:
            results.append((uid, "mentioned"))
            seen.add(uid)

    return results


def _attach_identities_to_event(conn, event_id: str,
                                 identities: list[tuple[str, str]]):
    for identity_id, role in identities:
        conn.execute("""
            INSERT INTO event_identity (event_id, identity_id, role)
            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
        """, (event_id, identity_id, role))


# ── Claude 分類 ───────────────────────────────────────────────────

def _detect_group_and_mention(msg: dict) -> tuple[bool, bool]:
    """檢測是否為群組訊息，以及是否提及 Logos。
    回傳 (is_group, logos_mentioned)"""
    payload = msg.get("payload", {})
    to_type = payload.get("toType")
    is_group = to_type == 2 or payload.get("to", "").startswith("C")

    text = msg.get("text", "").lower()
    logos_mentioned = any(name.lower() in text for name in ["logos", "羅格致", "陳佑竹", "@陳佑竹"])

    return is_group, logos_mentioned


def _classify(prompt_template: str, sender_name: str, text: str,
              is_group: bool = False, group_name: str = "", logos_mentioned: bool = True) -> tuple[str, str, str]:
    """回傳 (category, priority, summary)。"""
    import subprocess
    context = f"發送者：{sender_name}\n訊息：{text}"
    if is_group:
        context += f"\n（群組：{group_name}，Logos {'被提及' if logos_mentioned else '未被提及'}）"

    prompt = f"{prompt_template}\n\n{context}"
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
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


# ── Judge ─────────────────────────────────────────────────────────

def _judge_topic(conn, topic_id: str, judge_prompt: str) -> dict | None:
    """
    把 topic + messages 給 Claude 判斷是否需要建 event。
    回傳 {"needs_action": bool, "priority": str, "action": str} 或 None。
    """
    import subprocess

    row = conn.execute(
        "SELECT summary, category FROM topic WHERE id = %s", (topic_id,)
    ).fetchone()
    if not row:
        return None
    summary, category = row

    msgs = conn.execute("""
        SELECT sender_name, text, sent_at FROM topic_message
        WHERE topic_id = %s ORDER BY sent_at ASC
    """, (topic_id,)).fetchall()

    msgs_text = "\n".join(
        f"[{sent_at.strftime('%H:%M')}] {sender}: {text}"
        for sender, text, sent_at in msgs
    )

    prompt = f"{judge_prompt}\n\n## Topic\ncategory: {category}\nsummary: {summary}\n\n## 訊息記錄\n{msgs_text}"
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        raw = result.stdout.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"[scanner] judge 失敗：{e}", file=sys.stderr)
        return None


def _create_event_from_topic(conn, topic_id: str, summary: str,
                              priority: str, action: str,
                              occurred_at: datetime,
                              identities: list[tuple[str, str]]):
    row = conn.execute("""
        INSERT INTO event (topic_id, summary, category, priority, occurred_at)
        SELECT %s, %s, category, %s, %s FROM topic WHERE id = %s
        RETURNING id
    """, (topic_id, f"{summary}（{action}）", priority, occurred_at, topic_id)).fetchone()
    event_id = str(row[0])
    _attach_identities_to_event(conn, event_id, identities)
    conn.execute(
        "UPDATE topic SET state = 'judged' WHERE id = %s", (topic_id,)
    )
    conn.commit()
    return event_id


# ── 即時通知 ──────────────────────────────────────────────────────

def _alert_ruocosi(summary: str):
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


# ── Settle check ─────────────────────────────────────────────────

def settle_and_judge(conn, judge_prompt: str, identity_map: dict[str, str]):
    """找 accumulating topic 超過 SETTLE_MINUTES 的，settled → judge。"""
    rows = conn.execute("""
        SELECT id FROM topic
        WHERE state = 'accumulating'
          AND last_seen_at < NOW() - INTERVAL '1 minute' * %s
    """, (SETTLE_MINUTES,)).fetchall()

    for (topic_id,) in rows:
        conn.execute(
            "UPDATE topic SET state = 'settled', settled_at = NOW() WHERE id = %s",
            (topic_id,)
        )
        conn.commit()

        verdict = _judge_topic(conn, str(topic_id), judge_prompt)
        if not verdict or not verdict.get("needs_action"):
            conn.execute(
                "UPDATE topic SET state = 'judged' WHERE id = %s", (topic_id,)
            )
            conn.commit()
            print(f"[scanner] topic {str(topic_id)[:8]}… 不需行動，跳過")
            continue

        priority = verdict.get("priority", "normal")
        action   = verdict.get("action", "")

        # 收集 topic 的所有 identity
        msg_rows = conn.execute("""
            SELECT sender_name, text FROM topic_message WHERE topic_id = %s
        """, (topic_id,)).fetchall()
        identities: list[tuple[str, str]] = []
        for sender, text in msg_rows:
            identities += _extract_identities(text or "", sender or "", identity_map)

        topic_row = conn.execute(
            "SELECT summary, first_seen_at FROM topic WHERE id = %s", (topic_id,)
        ).fetchone()
        summary, occurred_at = topic_row

        event_id = _create_event_from_topic(
            conn, str(topic_id), summary, priority, action, occurred_at, identities
        )
        print(f"[scanner] [{priority}] event 建立 {event_id[:8]}… {summary[:40]}")

        if priority in ("high", "critical"):
            _alert_ruocosi(f"{summary}（{action}）")


# ── 主掃描邏輯 ────────────────────────────────────────────────────

def scan_once():
    from embed import encode

    since_ts = int((time.time() - LOOKBACK_MINUTES * 60) * 1000)

    try:
        convs = httpx.get(f"{CHANNEL_API}/conversations", timeout=10).json()
    except Exception as e:
        print(f"[scanner] 無法取得 conversations：{e}", file=sys.stderr)
        return

    processed = skipped = 0

    with _conn() as conn:
        classify_prompt = _load_prompt(conn, "classifier")
        judge_prompt    = _load_prompt(conn, "judge")
        identity_map    = _load_identity_map(conn)

        for conv in convs:
            conv_id = conv["conversation_id"]
            try:
                msgs = httpx.get(
                    f"{CHANNEL_API}/conversations/{conv_id}/messages",
                    params={"limit": 50}, timeout=10,
                ).json()
            except Exception as e:
                print(f"[scanner] {conv_id[:8]} 讀取失敗：{e}", file=sys.stderr)
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
                occurred_at = datetime.fromtimestamp(
                    msg["created_at"] / 1000, tz=timezone.utc
                )

                # 群組訊息預篩：未提及 Logos 則跳過
                is_group, logos_mentioned = _detect_group_and_mention(msg)
                if is_group and not logos_mentioned:
                    skipped += 1
                    continue

                category, priority, summary = _classify(
                    classify_prompt, sender, msg["text"],
                    is_group=is_group, group_name=conv.get("display_name", ""), logos_mentioned=logos_mentioned
                )

                if category == "social" and priority == "low":
                    skipped += 1
                    continue

                # 找 topic
                embedding = encode(summary)
                topic_id = (
                    _find_topic_by_conversation(conn, conv_id, category)
                    or _find_topic_by_embedding(conn, embedding, category)
                )

                if topic_id:
                    _attach_to_topic(conn, topic_id, msg, sender, summary, occurred_at)
                    print(f"[scanner] 掛入 topic {topic_id[:8]}… {summary[:30]}")
                else:
                    topic_id = _create_topic(conn, summary, category, embedding, occurred_at)
                    _attach_to_topic(conn, topic_id, msg, sender, summary, occurred_at)
                    print(f"[scanner] 新 topic {topic_id[:8]}… [{category}] {summary[:30]}")

                processed += 1

                # critical：不等 settle，立刻 judge
                if priority == "critical":
                    conn.execute(
                        "UPDATE topic SET state = 'settled', settled_at = NOW() WHERE id = %s",
                        (topic_id,)
                    )
                    conn.commit()
                    identities = _extract_identities(
                        msg.get("text", ""), sender, identity_map
                    )
                    verdict = _judge_topic(conn, topic_id, judge_prompt)
                    if verdict and verdict.get("needs_action"):
                        event_id = _create_event_from_topic(
                            conn, topic_id, summary,
                            verdict.get("priority", "critical"),
                            verdict.get("action", ""),
                            occurred_at, identities,
                        )
                        _alert_ruocosi(f"{summary}（{verdict.get('action', '')}）")
                        print(f"[scanner] [critical] event {event_id[:8]}…")

        # settle check
        settle_and_judge(conn, judge_prompt, identity_map)

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
