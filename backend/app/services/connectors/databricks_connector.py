"""Databricks connector.

Pulls compute and storage costs from the Databricks Billable Usage API.
Credentials: account_id + access_token (from Databricks Account Console > Settings > API).
Works for both AWS and Azure Databricks.
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector

# Databricks DBU pricing (approximate, varies by plan and cloud)
DBU_PRICING = {
    "ALL_PURPOSE": 0.55,       # $/DBU for all-purpose compute
    "JOBS": 0.30,              # $/DBU for jobs compute
    "SQL": 0.22,               # $/DBU for SQL warehouse
    "DLT": 0.36,               # $/DBU for Delta Live Tables
    "MODEL_SERVING": 0.07,     # $/DBU for model serving
    "INTERACTIVE": 0.55,       # $/DBU for interactive (notebooks)
    "SERVERLESS_SQL": 0.70,    # $/DBU for serverless SQL
    "SERVERLESS_COMPUTE": 0.70,
    "FOUNDATION_MODEL": 0.07,  # $/DBU for Foundation Model APIs
}


class DatabricksConnector(BaseConnector):
    platform = "databricks"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.account_id = credentials["account_id"]
        self.access_token = credentials["access_token"]
        # Account-level API for billing
        self.accounts_url = f"https://accounts.cloud.databricks.com/api/2.0/accounts/{self.account_id}"
        # Workspace URL for workspace-level queries
        self.workspace_url = credentials.get("workspace_url", "")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> dict:
        try:
            resp = httpx.get(
                f"{self.accounts_url}/usage/download",
                headers=self._headers(),
                params={
                    "start_month": datetime.utcnow().strftime("%Y-%m"),
                    "end_month": datetime.utcnow().strftime("%Y-%m"),
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "Databricks connection successful"}
            # Try workspace API as fallback
            if self.workspace_url:
                resp = httpx.get(
                    f"{self.workspace_url}/api/2.0/clusters/list",
                    headers=self._headers(),
                    timeout=10,
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "Databricks workspace connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch Databricks usage from the Billable Usage API.

        Downloads CSV usage data and parses into UnifiedCost records.
        """
        costs = []

        try:
            costs = self._fetch_from_usage_api(days)
            if costs:
                return costs
        except Exception:
            pass

        # Fallback: try workspace-level cluster costs
        if self.workspace_url:
            try:
                costs = self._fetch_from_workspace(days)
            except Exception:
                pass

        return costs

    def _fetch_from_usage_api(self, days: int) -> list[UnifiedCost]:
        """Fetch from Databricks Account-level Usage API."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        resp = httpx.get(
            f"{self.accounts_url}/usage/download",
            headers=self._headers(),
            params={
                "start_month": start.strftime("%Y-%m"),
                "end_month": end.strftime("%Y-%m"),
            },
            timeout=30,
        )

        if resp.status_code != 200:
            return []

        # Parse CSV response
        import csv
        import io

        reader = csv.DictReader(io.StringIO(resp.text))
        daily = {}

        for row in reader:
            date = row.get("usage_date", "")
            if not date or date < start.strftime("%Y-%m-%d"):
                continue

            sku = row.get("sku_name", "UNKNOWN").upper()
            dbu = float(row.get("usage_quantity", 0))
            workspace = row.get("workspace_name", "default")
            cluster_name = row.get("cluster_name", row.get("usage_metadata", {}).get("cluster_id", "unknown"))

            # Map SKU to category
            category = CostCategory.compute
            for sku_key in ("SQL", "SERVERLESS_SQL"):
                if sku_key in sku:
                    category = CostCategory.compute
                    break
            for sku_key in ("DLT",):
                if sku_key in sku:
                    category = CostCategory.transformation
                    break
            for sku_key in ("MODEL_SERVING", "FOUNDATION_MODEL"):
                if sku_key in sku:
                    category = CostCategory.ml_serving
                    break

            # Estimate cost from DBU
            price_per_dbu = DBU_PRICING.get(sku, 0.40)
            cost = round(dbu * price_per_dbu, 4)

            key = f"{date}|{workspace}|{sku}"
            if key not in daily:
                daily[key] = {
                    "date": date,
                    "workspace": workspace,
                    "sku": sku,
                    "category": category,
                    "dbu": 0,
                    "cost": 0,
                }
            daily[key]["dbu"] += dbu
            daily[key]["cost"] += cost

        costs = []
        for entry in daily.values():
            if entry["cost"] == 0 and entry["dbu"] == 0:
                continue

            costs.append(UnifiedCost(
                date=entry["date"],
                platform="databricks",
                service=f"databricks_{entry['sku'].lower()}",
                resource=entry["workspace"],
                category=entry["category"],
                cost_usd=round(entry["cost"], 4),
                usage_quantity=round(entry["dbu"], 4),
                usage_unit="DBU",
                metadata={
                    "sku": entry["sku"],
                    "workspace": entry["workspace"],
                },
            ))

        return costs

    def _fetch_from_workspace(self, days: int) -> list[UnifiedCost]:
        """Fallback: fetch cluster runtime from workspace API."""
        resp = httpx.get(
            f"{self.workspace_url}/api/2.0/clusters/list",
            headers=self._headers(),
            timeout=15,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        costs = []
        today = datetime.utcnow().strftime("%Y-%m-%d")

        for cluster in data.get("clusters", []):
            cluster_name = cluster.get("cluster_name", "unknown")
            state = cluster.get("state", "")
            node_type = cluster.get("node_type_id", "")
            num_workers = cluster.get("num_workers", 0)
            autotermination_min = cluster.get("autotermination_minutes", 0)

            # Rough uptime estimate from last activity
            last_activity = cluster.get("last_activity_time", 0)
            if last_activity:
                uptime_hours = max(0, (datetime.utcnow().timestamp() * 1000 - last_activity) / 3_600_000)
            else:
                uptime_hours = 0

            # Estimate DBU from workers and uptime
            dbu_per_hour = (num_workers + 1) * 0.5  # rough
            dbu = round(dbu_per_hour * min(uptime_hours, 24), 2)
            cost = round(dbu * 0.40, 4)

            if cost == 0:
                continue

            costs.append(UnifiedCost(
                date=today,
                platform="databricks",
                service="databricks_cluster",
                resource=cluster_name,
                category=CostCategory.compute,
                cost_usd=cost,
                usage_quantity=dbu,
                usage_unit="DBU",
                metadata={
                    "state": state,
                    "node_type": node_type,
                    "num_workers": num_workers,
                },
            ))

        return costs
