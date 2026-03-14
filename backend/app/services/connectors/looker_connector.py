"""Looker connector.

Pulls query usage and license costs from the Looker Admin API.
Credentials: client_id + client_secret + instance_url
(from Looker Admin > API Keys).
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector


class LookerConnector(BaseConnector):
    platform = "looker"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.client_id = credentials["client_id"]
        self.client_secret = credentials["client_secret"]
        self.instance_url = credentials["instance_url"].rstrip("/")
        self._token = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = httpx.post(
            f"{self.instance_url}/api/4.0/login",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"token {self._get_token()}"}

    def test_connection(self) -> dict:
        try:
            token = self._get_token()
            resp = httpx.get(
                f"{self.instance_url}/api/4.0/user",
                headers={"Authorization": f"token {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "Looker connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch Looker usage metrics.

        Tracks: query volume, PDT builds, user count.
        Looker cost is license-based, so we attribute by usage.
        """
        costs = []

        try:
            # Get system usage stats
            query_stats = self._get_query_stats(days)
            user_count = self._get_user_count()
            pdt_builds = self._get_pdt_builds(days)
        except Exception:
            return costs

        # Looker pricing: ~$5K-50K/mo depending on seats + usage
        # We estimate based on user count: ~$125/user/month
        monthly_cost = user_count * 125.0
        daily_cost = round(monthly_cost / 30, 2)

        # Distribute cost by query volume per day
        total_queries = sum(s.get("count", 0) for s in query_stats)
        if total_queries == 0:
            total_queries = 1

        for stat in query_stats:
            date = stat.get("date", "")
            query_count = stat.get("count", 0)
            weight = query_count / total_queries if total_queries > 0 else 1 / max(len(query_stats), 1)
            cost = round(daily_cost * weight * len(query_stats), 4)

            costs.append(UnifiedCost(
                date=date,
                platform="looker",
                service="looker",
                resource="queries",
                category=CostCategory.serving,
                cost_usd=cost if cost > 0 else daily_cost,
                usage_quantity=query_count,
                usage_unit="queries",
                metadata={
                    "user_count": user_count,
                    "query_count": query_count,
                },
            ))

        # PDT build costs (BigQuery compute attributed to Looker)
        for build in pdt_builds:
            date = build.get("date", "")
            build_count = build.get("count", 0)

            costs.append(UnifiedCost(
                date=date,
                platform="looker",
                service="looker_pdt",
                resource="pdt_builds",
                category=CostCategory.transformation,
                cost_usd=0,  # Actual compute cost is in BigQuery/Snowflake
                usage_quantity=build_count,
                usage_unit="builds",
                metadata={"pdt_builds": build_count},
            ))

        return costs

    def _get_query_stats(self, days: int) -> list[dict]:
        """Get daily query counts from system activity."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Use the System Activity model via inline query
        resp = httpx.post(
            f"{self.instance_url}/api/4.0/queries/run/json",
            headers=self._headers(),
            json={
                "model": "system__activity",
                "view": "history",
                "fields": ["history.created_date", "history.query_run_count"],
                "filters": {
                    "history.created_date": f"after {start.strftime('%Y-%m-%d')}",
                },
                "sorts": ["history.created_date asc"],
                "limit": str(days + 1),
            },
            timeout=30,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        return [
            {
                "date": row.get("history.created_date", ""),
                "count": row.get("history.query_run_count", 0),
            }
            for row in data
        ]

    def _get_user_count(self) -> int:
        """Get active user count."""
        resp = httpx.get(
            f"{self.instance_url}/api/4.0/users?fields=id&is_disabled=false",
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            return 0
        return len(resp.json())

    def _get_pdt_builds(self, days: int) -> list[dict]:
        """Get PDT build activity."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        resp = httpx.post(
            f"{self.instance_url}/api/4.0/queries/run/json",
            headers=self._headers(),
            json={
                "model": "system__activity",
                "view": "pdt_event_log",
                "fields": ["pdt_event_log.created_date", "pdt_event_log.count"],
                "filters": {
                    "pdt_event_log.created_date": f"after {start.strftime('%Y-%m-%d')}",
                    "pdt_event_log.action": "create",
                },
                "sorts": ["pdt_event_log.created_date asc"],
                "limit": str(days + 1),
            },
            timeout=30,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        return [
            {
                "date": row.get("pdt_event_log.created_date", ""),
                "count": row.get("pdt_event_log.count", 0),
            }
            for row in data
        ]
