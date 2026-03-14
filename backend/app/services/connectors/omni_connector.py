"""Omni Analytics connector.

Pulls query usage from Omni's REST API.
Credentials: api_key + instance_url (from Omni Admin > API Keys).
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector


class OmniConnector(BaseConnector):
    platform = "omni"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key = credentials["api_key"]
        self.instance_url = credentials["instance_url"].rstrip("/")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def test_connection(self) -> dict:
        try:
            resp = httpx.get(
                f"{self.instance_url}/api/v0/connections",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "Omni connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch Omni usage metrics.

        Tracks queries and user activity.
        Omni pricing is seat-based (~$35-75/user/month).
        """
        costs = []

        try:
            users = self._get_users()
            query_stats = self._get_query_stats(days)
        except Exception:
            return costs

        user_count = len(users)
        monthly_cost = user_count * 50.0  # ~$50/user/month average
        daily_cost = round(monthly_cost / 30, 2)

        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Daily records
        current = start
        while current < end:
            date = current.strftime("%Y-%m-%d")
            day_queries = sum(1 for q in query_stats if q.get("date") == date)

            costs.append(UnifiedCost(
                date=date,
                platform="omni",
                service="omni",
                resource="analytics",
                category=CostCategory.serving,
                cost_usd=daily_cost,
                usage_quantity=day_queries or user_count,
                usage_unit="queries" if day_queries else "users",
                metadata={
                    "user_count": user_count,
                    "queries": day_queries,
                },
            ))
            current += timedelta(days=1)

        return costs

    def _get_users(self) -> list[dict]:
        """Get active users."""
        resp = httpx.get(
            f"{self.instance_url}/api/v0/users",
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data if isinstance(data, list) else data.get("users", [])

    def _get_query_stats(self, days: int) -> list[dict]:
        """Get query execution history."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        resp = httpx.get(
            f"{self.instance_url}/api/v0/queries",
            headers=self._headers(),
            params={
                "created_after": start.strftime("%Y-%m-%dT00:00:00Z"),
                "limit": 1000,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        queries = data if isinstance(data, list) else data.get("queries", [])
        return [
            {"date": q.get("created_at", "")[:10]}
            for q in queries
        ]
