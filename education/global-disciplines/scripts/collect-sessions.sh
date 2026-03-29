#!/bin/sh
# collect-sessions.sh — 找出上次掃描後的新 session，提取訊息摘要
# 供 ai-evaluate 類排程任務使用，輸出至 stdout

SESSIONS_ROOT="$HOME/.claude/projects"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE_FILE="$SCRIPT_DIR/../.session-scan-state"

# 上次掃描時間（unix timestamp），預設 7 天前
if [ -f "$STATE_FILE" ]; then
    LAST_SCAN=$(cat "$STATE_FILE")
else
    LAST_SCAN=$(date -d '7 days ago' +%s 2>/dev/null || date -v-7d +%s 2>/dev/null || echo 0)
fi

# 更新掃描時間
date +%s > "$STATE_FILE"

# 用 Python 提取 session 摘要
python3 << PYEOF
import os, json, time

sessions_root = "$SESSIONS_ROOT"
last_scan = int("$LAST_SCAN")

results = []
for proj_dir in sorted(os.listdir(sessions_root)):
    proj_path = os.path.join(sessions_root, proj_dir)
    if not os.path.isdir(proj_path):
        continue
    for fname in os.listdir(proj_path):
        if not fname.endswith('.jsonl'):
            continue
        fpath = os.path.join(proj_path, fname)
        mtime = int(os.path.getmtime(fpath))
        if mtime <= last_scan:
            continue
        # 提取前 5 則 user 訊息
        msgs = []
        try:
            with open(fpath) as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        if d.get('type') == 'user':
                            content = d.get('message', {}).get('content', '')
                            if isinstance(content, list):
                                text = ' '.join(c.get('text','') for c in content if isinstance(c,dict) and c.get('type')=='text')
                            else:
                                text = str(content)
                            text = text.strip()[:300]
                            if text and not text.startswith('<'):
                                msgs.append(text)
                                if len(msgs) >= 5:
                                    break
                    except:
                        pass
        except:
            continue
        if msgs:
            results.append({
                'project': proj_dir,
                'session': fname.replace('.jsonl', ''),
                'modified': time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime)),
                'messages': msgs
            })

if not results:
    print("(此週期內無新 session)")
else:
    print(f"## 新 Sessions（共 {len(results)} 個）\n")
    for r in results:
        print(f"### {r['project']} / {r['session']}")
        print(f"**更新時間**：{r['modified']}\n")
        for i, msg in enumerate(r['messages'], 1):
            print(f"{i}. {msg}")
        print()
PYEOF
