#!/usr/bin/env python3
"""
schedule-check.py — 判斷任務是否應於現在執行
Usage: python3 schedule-check.py <manifest_path> [reports_dir]
Exit 0 = 應執行, Exit 1 = 不需執行
"""
import re, sys, os
from datetime import datetime, timedelta

def field(content, key):
    m = re.search(rf'^{key}:\s*["\']?([^"\'\n]+)["\']?', content, re.MULTILINE)
    return m.group(1).strip() if m else ''

def cron_match(expr, now):
    parts = expr.strip().split()
    if len(parts) != 5:
        return False
    def check(f, v):
        if f == '*': return True
        if '/' in f:
            b, s = f.split('/', 1)
            start = 0 if b == '*' else int(b)
            return (v - start) % int(s) == 0 and v >= start
        if ',' in f:
            return any(check(x, v) for x in f.split(','))
        if '-' in f:
            a, b = f.split('-')
            return int(a) <= v <= int(b)
        return int(f) == v
    mn, hr, dom, mo, dow = parts
    return (check(mn, now.minute) and check(hr, now.hour) and
            check(dom, now.day) and check(mo, now.month) and
            check(dow, now.weekday()))

def last_run(task_name, reports_dir):
    """從 reports/ 找最近一次執行時間"""
    latest = None
    if not os.path.isdir(reports_dir):
        return None
    for d in sorted(os.listdir(reports_dir), reverse=True):
        rpt = os.path.join(reports_dir, d, f"{task_name}.md")
        if os.path.exists(rpt):
            m = re.search(r'^timestamp:\s*(.+)', open(rpt).read(), re.MULTILINE)
            if m:
                try: return datetime.fromisoformat(m.group(1).strip().replace('Z', '+00:00'))
                except: pass
            latest = datetime.strptime(d, '%Y%m%d')
            return latest
    return None

manifest_path = sys.argv[1]
reports_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(manifest_path), '../reports')

content = open(manifest_path).read()
enabled = field(content, 'enabled')
if enabled == 'false':
    sys.exit(1)

stype = field(content, r'schedule:\s*\n\s*type') or field(content, 'type')
# simpler: extract from nested yaml
m = re.search(r'schedule:\s*\n\s*type:\s*["\']?([^"\'\s]+)["\']?', content)
stype = m.group(1) if m else ''
m = re.search(r'schedule:\s*\n[^\n]*\n\s*expr:\s*["\']?([^"\'\\n]+)["\']?', content)
expr = m.group(1).strip().strip('"\'') if m else ''

task_name = field(content, 'task_name')
now = datetime.now().astimezone()

if stype == 'cron':
    sys.exit(0 if cron_match(expr, now) else 1)

elif stype == 'interval':
    # 解析 interval: 1d / 4h / 30m
    m = re.match(r'(\d+)([dhm])', expr)
    if not m:
        sys.exit(1)
    n, unit = int(m.group(1)), m.group(2)
    delta = {'d': timedelta(days=n), 'h': timedelta(hours=n), 'm': timedelta(minutes=n)}[unit]
    lr = last_run(task_name, reports_dir)
    if lr is None:
        sys.exit(0)  # 從未執行 → 立即執行
    age = now.replace(tzinfo=None) - lr.replace(tzinfo=None)
    sys.exit(0 if age >= delta else 1)

elif stype == 'one-time':
    today = now.strftime('%Y-%m-%d')
    rpt = os.path.join(reports_dir, today.replace('-', ''), f"{task_name}.md")
    sys.exit(0 if expr == today and not os.path.exists(rpt) else 1)

sys.exit(1)
