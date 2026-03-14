"""dbt Cloud connector.

Pulls job run history and computes transformation costs from
dbt Cloud's Admin API.
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector


class DbtCloudConnector(BaseConnector):
    platform = "dbt_cloud"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_token = credentials["api_token"]
        self.account_id = credentials["account_id"]
        self.base_url = f"https://cloud.getdbt.com/api/v2/accounts/{self.account_id}"

    def _headers(self):
        return {"Authorization": f"Token {self.api_token}"}

    def test_connection(self) -> dict:
        try:
            resp = httpx.get(
                f"https://cloud.getdbt.com/api/v2/accounts/{self.account_id}/",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "dbt Cloud connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch dbt Cloud job runs and estimate costs.

        dbt Cloud doesn't expose cost directly — we track run duration
        and model count as usage, and the user can set their dbt Cloud
        plan cost to calculate per-run attribution.
        """
        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")

        runs = []
        offset = 0
        while True:
            resp = httpx.get(
                f"{self.base_url}/runs/",
                headers=self._headers(),
                params={
                    "created_after": since,
                    "limit": 100,
                    "offset": offset,
                    "order_by": "-created_at",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                break
            data = resp.json().get("data", [])
            if not data:
                break
            runs.extend(data)
            offset += 100
            if len(data) < 100:
                break

        # Group runs by date and job
        daily_costs = {}
        for run in runs:
            if run.get("status") != 10:  # 10 = success
                continue
            date = run["created_at"][:10]
            job_name = run.get("job", {}).get("name", f"job_{run.get('job_id', 'unknown')}")
            duration_s = run.get("duration", 0)
            models = run.get("run_results_count", 0) or 0

            key = (date, job_name)
            if key not in daily_costs:
                daily_costs[key] = {"duration_s": 0, "models": 0, "runs": 0}
            daily_costs[key]["duration_s"] += duration_s
            daily_costs[key]["models"] += models
            daily_costs[key]["runs"] += 1

        costs = []
        for (date, job_name), stats in daily_costs.items():
            # dbt Cloud pricing: ~$100-500/mo depending on plan
            # We track run minutes as the usage metric; cost attribution
            # can be set by the user based on their plan
            run_minutes = stats["duration_s"] / 60

            costs.append(UnifiedCost(
                date=date,
                platform="dbt_cloud",
                service="dbt_cloud",
                resource=job_name,
                category=CostCategory.transformation,
                cost_usd=0.0,  # User configures plan cost; we do attribution
                usage_quantity=round(run_minutes, 2),
                usage_unit="run_minutes",
                metadata={
                    "runs": stats["runs"],
                    "models_executed": stats["models"],
                    "total_duration_seconds": stats["duration_s"],
                },
            ))

        return costs
