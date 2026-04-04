"""BigQuery billing export 查詢。"""
import json
import os
from datetime import datetime, timezone

from google.cloud import bigquery


def _config():
    with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
        return json.load(f)


def fetch_monthly_costs() -> list[dict]:
    """回傳本月各 project 淨費用（cost - credits）。

    Returns:
        [{"project_id": str, "cost": float, "currency": str}, ...]
    """
    cfg = _config()
    client = bigquery.Client(project=cfg["bigquery_project"])

    account_id = cfg["billing_account"].replace("-", "_")
    table = (
        f"`{cfg['bigquery_project']}.{cfg['bigquery_dataset']}"
        f".gcp_billing_export_v1_{account_id}`"
    )
    invoice_month = datetime.now(timezone.utc).strftime("%Y%m")

    query = f"""
    SELECT
      project.id AS project_id,
      SUM(cost) + SUM(
        IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) AS c), 0)
      ) AS net_cost,
      ANY_VALUE(currency) AS currency
    FROM {table}
    WHERE invoice.month = @invoice_month
    GROUP BY project.id
    ORDER BY net_cost DESC
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("invoice_month", "STRING", invoice_month)
        ]
    )
    rows = client.query(query, job_config=job_cfg).result()
    return [
        {"project_id": r.project_id, "cost": float(r.net_cost or 0), "currency": r.currency}
        for r in rows
    ]
