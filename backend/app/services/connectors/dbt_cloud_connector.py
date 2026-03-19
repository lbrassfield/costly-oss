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
                    # include_related=job embeds the job object so run["job"]["name"] is populated
                    "include_related": "job",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                break
            body = resp.json()
            data = body.get("data", [])
            if not data:
                break
            runs.extend(data)
            total_count = (
                body.get("extra", {}).get("pagination", {}).get("total_count", 0)
            )
            offset += 100
            # Stop if we've fetched all runs or the page was a partial page
            if len(data) < 100 or offset >= total_count:
                break

        # Completed statuses: 10=Success, 20=Error, 30=Cancelled
        COMPLETED_STATUSES = {10, 20, 30}
        STATUS_LABELS = {10: "success", 20: "error", 30: "cancelled"}

        # Group runs by date and job
        daily_costs: dict = {}
        for run in runs:
            status = run.get("status")
            if status not in COMPLETED_STATUSES:
                continue
            date = run["created_at"][:10]
            job_name = run.get("job", {}).get("name", f"job_{run.get('job_id', 'unknown')}")
            # duration = total wall-clock time (queue + execution)
            # run_duration = execution-only time (excludes queue wait)
            duration_s = run.get("duration", 0) or 0
            run_duration_s = run.get("run_duration", 0) or 0
            queued_duration_s = max(0, duration_s - run_duration_s)

            key = (date, job_name)
            if key not in daily_costs:
                daily_costs[key] = {
                    "duration_s": 0,
                    "run_duration_s": 0,
                    "queued_duration_s": 0,
                    "runs": 0,
                    "errors": 0,
                    "cancelled": 0,
                }
            daily_costs[key]["duration_s"] += duration_s
            daily_costs[key]["run_duration_s"] += run_duration_s
            daily_costs[key]["queued_duration_s"] += queued_duration_s
            daily_costs[key]["runs"] += 1
            if status == 20:
                daily_costs[key]["errors"] += 1
            elif status == 30:
                daily_costs[key]["cancelled"] += 1

        costs = []
        for (date, job_name), stats in daily_costs.items():
            run_minutes = stats["duration_s"] / 60

            # dbt Cloud Starter plan charges ~$0.01 per successful model built.
            # The runs endpoint does not return model counts — the artifacts
            # endpoint (/runs/{id}/artifacts/) would be needed but requires one
            # request per run, which is too expensive. Model count is set to 0.
            models_executed = 0  # artifacts endpoint required for actual count

            # Cost estimate: use execution duration as a proxy for compute cost.
            # Rough estimate: $0.50 per compute-hour (varies by plan).
            # This is an estimate only — actual billing depends on dbt Cloud plan.
            cost_usd = round(stats["run_duration_s"] / 3600 * 0.50, 6)

            costs.append(UnifiedCost(
                date=date,
                platform="dbt_cloud",
                service="dbt_cloud",
                resource=job_name,
                category=CostCategory.transformation,
                cost_usd=cost_usd,
                usage_quantity=round(run_minutes, 2),
                usage_unit="run_minutes",
                metadata={
                    "runs": stats["runs"],
                    "errors": stats["errors"],
                    "cancelled": stats["cancelled"],
                    "models_executed": models_executed,
                    "total_duration_seconds": stats["duration_s"],
                    "execution_duration_seconds": stats["run_duration_s"],
                    "queued_duration_seconds": stats["queued_duration_s"],
                    "cost_is_estimate": True,
                },
            ))

        return costs
