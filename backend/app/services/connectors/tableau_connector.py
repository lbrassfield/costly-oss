"""Tableau connector.

Pulls usage metrics from Tableau Server/Cloud REST API.
Credentials: server_url + personal_access_token_name + personal_access_token_secret + site_id
(from Tableau Account Settings > Personal Access Tokens).
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector


class TableauConnector(BaseConnector):
    platform = "tableau"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.server_url = credentials["server_url"].rstrip("/")
        self.token_name = credentials["token_name"]
        self.token_secret = credentials["token_secret"]
        self.site_id = credentials.get("site_id", "")
        self._auth_token = None
        self._site_id = None

    def _authenticate(self):
        """Sign in and get auth token."""
        if self._auth_token:
            return

        body = {
            "credentials": {
                "personalAccessTokenName": self.token_name,
                "personalAccessTokenSecret": self.token_secret,
                "site": {"contentUrl": self.site_id},
            }
        }
        resp = httpx.post(
            f"{self.server_url}/api/3.22/auth/signin",
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        creds = data.get("credentials", {})
        self._auth_token = creds.get("token")
        self._site_id = creds.get("site", {}).get("id")

    def _headers(self) -> dict:
        self._authenticate()
        return {"X-Tableau-Auth": self._auth_token}

    def _api_url(self, path: str) -> str:
        return f"{self.server_url}/api/3.22/sites/{self._site_id}{path}"

    def test_connection(self) -> dict:
        try:
            self._authenticate()
            resp = httpx.get(
                self._api_url("/users?pageSize=1"),
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "Tableau connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch Tableau usage metrics.

        Tracks: user count, view access, extract refreshes.
        Tableau is license-based — we distribute cost by usage.
        """
        costs = []

        try:
            self._authenticate()
            user_count = self._get_user_count()
            views_data = self._get_view_usage(days)
            extract_refreshes = self._get_extract_refreshes(days)
        except Exception:
            return costs

        # Tableau pricing: Creator $75/user/mo, Explorer $42, Viewer $15
        # Average ~$35/user/mo blended
        monthly_cost = user_count * 35.0
        daily_cost = round(monthly_cost / 30, 2)

        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Daily license cost
        current = start
        while current < end:
            date = current.strftime("%Y-%m-%d")
            day_views = sum(1 for v in views_data if v.get("date") == date)

            costs.append(UnifiedCost(
                date=date,
                platform="tableau",
                service="tableau",
                resource="licenses",
                category=CostCategory.licensing,
                cost_usd=daily_cost,
                usage_quantity=user_count,
                usage_unit="users",
                metadata={
                    "user_count": user_count,
                    "view_accesses": day_views,
                },
            ))
            current += timedelta(days=1)

        # Extract refresh activity (triggers compute on connected warehouse)
        for refresh in extract_refreshes:
            date = refresh.get("date", "")
            count = refresh.get("count", 0)

            costs.append(UnifiedCost(
                date=date,
                platform="tableau",
                service="tableau_extracts",
                resource="extract_refreshes",
                category=CostCategory.serving,
                cost_usd=0,  # Compute cost is on the warehouse side
                usage_quantity=count,
                usage_unit="refreshes",
                metadata={"extract_refreshes": count},
            ))

        return costs

    def _get_user_count(self) -> int:
        """Get total user count."""
        resp = httpx.get(
            self._api_url("/users?pageSize=1"),
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            return 0
        data = resp.json()
        return int(data.get("pagination", {}).get("totalAvailable", 0))

    def _get_view_usage(self, days: int) -> list[dict]:
        """Get view usage stats."""
        resp = httpx.get(
            self._api_url("/views?includeUsageStatistics=true&pageSize=100"),
            headers=self._headers(),
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        views = data.get("views", {}).get("view", [])
        return [
            {
                "name": v.get("name", ""),
                "total_views": v.get("usage", {}).get("totalViewCount", 0),
            }
            for v in views
        ]

    def _get_extract_refreshes(self, days: int) -> list[dict]:
        """Get extract refresh tasks."""
        resp = httpx.get(
            self._api_url("/tasks/extractRefreshes?pageSize=100"),
            headers=self._headers(),
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        tasks = data.get("tasks", {}).get("task", [])

        # Aggregate by day
        daily = {}
        for task in tasks:
            schedule = task.get("extractRefresh", {})
            last_run = schedule.get("lastRunAt", "")
            if not last_run:
                continue
            date = last_run[:10]
            if date not in daily:
                daily[date] = {"date": date, "count": 0}
            daily[date]["count"] += 1

        return list(daily.values())
