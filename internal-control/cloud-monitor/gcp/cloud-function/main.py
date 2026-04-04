"""Cloud Function entry points.

daily_summary  — HTTP trigger（Cloud Scheduler 每日 09:00 觸發）
deploy_notify  — Pub/Sub trigger（Cloud Run audit log 部署事件）
"""
import base64
import calendar
import json
import logging
import os
from datetime import datetime, timezone

import functions_framework

import billing
import notifier

logging.basicConfig(level=logging.INFO)


def _config():
    with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
        return json.load(f)


# ── 每日費用摘要 ────────────────────────────────────────────────

@functions_framework.http
def daily_summary(request):
    cfg = _config()
    costs = billing.fetch_monthly_costs()

    now = datetime.now(timezone.utc)
    total_days = calendar.monthrange(now.year, now.month)[1]
    budgets = {p["id"]: p["budget_twd"] for p in cfg["projects"]}

    lines = [f"[雲端費用摘要] {now.strftime('%Y-%m-%d')}", f"本月累計（{now.month}月）："]

    total_cost = 0.0
    for row in costs:
        pid = row["project_id"] or "(未分類)"
        cost = row["cost"]
        currency = row.get("currency", "USD")
        total_cost += cost

        budget = budgets.get(pid)
        pct = f" / {budget} TWD ({int(cost / budget * 100)}%)" if budget else ""
        lines.append(f"  {pid}: {currency} {cost:.4f}{pct}")

    if now.day > 1 and total_cost > 0:
        daily_rate = total_cost / now.day
        projected = daily_rate * total_days
        lines.append(f"\n燒錢速度：{daily_rate:.4f}/天，月底預測 {projected:.4f}")

    if not costs:
        lines.append("  （本月尚無費用資料）")

    notifier.send("\n".join(lines))
    return ("ok", 200)


# ── 部署事件通知 ────────────────────────────────────────────────

@functions_framework.cloud_event
def deploy_notify(cloud_event):
    raw = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    entry = json.loads(raw)

    # 只處理操作完成的 log（跳過 operation.first）
    if entry.get("operation", {}).get("last") is False:
        return

    proto = entry.get("protoPayload", {})
    labels = entry.get("resource", {}).get("labels", {})

    service = labels.get("service_name", "unknown")
    project = labels.get("project_id", "unknown")
    caller  = proto.get("authenticationInfo", {}).get("principalEmail", "unknown")
    method  = proto.get("methodName", "")

    containers = (
        proto.get("request", {})
             .get("service", {})
             .get("spec", {})
             .get("template", {})
             .get("spec", {})
             .get("containers", [])
    )
    image = containers[0].get("image", "unknown") if containers else "unknown"

    action = "新建" if "Create" in method else "更新"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    notifier.send(
        f"[部署通知] {now}\n"
        f"動作：{action}\n"
        f"服務：{service}\n"
        f"專案：{project}\n"
        f"Image：{image}\n"
        f"部署者：{caller}"
    )
