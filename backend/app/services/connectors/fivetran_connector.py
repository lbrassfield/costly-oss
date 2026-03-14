"""Fivetran connector.

Pulls connector usage and costs from the Fivetran REST API v2.
Tracks MAR (Monthly Active Rows) and connector sync costs.
Credentials: api_key + api_secret (from Fivetran Account Settings > API Config).
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector


class FivetranConnector(BaseConnector):
    platform = "fivetran"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key = credentials["api_key"]
        self.api_secret = credentials["api_secret"]
        self.base_url = "https://api.fivetran.com/v1"

    def _headers(self) -> dict:
        return {"Accept": "application/json"}

    def _auth(self) -> tuple:
        return (self.api_key, self.api_secret)

    def test_connection(self) -> dict:
        try:
            resp = httpx.get(
                f"{self.base_url}/groups",
                auth=self._auth(),
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "Fivetran API connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch connector usage from Fivetran.

        Uses the usage endpoint to get MAR and sync data per connector.
        """
        costs = []

        # Get all groups (destinations)
        try:
            groups = self._get_groups()
        except Exception:
            return costs

        # Get connectors for each group
        for group in groups:
            group_id = group.get("id", "")
            group_name = group.get("name", group_id)

            try:
                connectors = self._get_connectors(group_id)
            except Exception:
                continue

            for connector in connectors:
                connector_id = connector.get("id", "")
                connector_name = connector.get("schema", connector_id)
                service = connector.get("service", "unknown")

                # Get usage stats for this connector
                try:
                    usage = self._get_connector_usage(connector_id, days)
                except Exception:
                    continue

                for entry in usage:
                    date = entry.get("date", "")
                    mar = entry.get("monthly_active_rows", 0)
                    sync_count = entry.get("syncs", 0)
                    cost = entry.get("cost", 0.0)

                    # If Fivetran doesn't return cost, estimate from MAR
                    # Fivetran pricing: ~$1 per 1M MAR (varies by plan)
                    if cost == 0 and mar > 0:
                        cost = round((mar / 1_000_000) * 1.0, 4)

                    if cost == 0 and mar == 0:
                        continue

                    costs.append(UnifiedCost(
                        date=date,
                        platform="fivetran",
                        service=f"fivetran_{service}",
                        resource=f"{group_name}/{connector_name}",
                        category=CostCategory.ingestion,
                        cost_usd=round(cost, 4),
                        usage_quantity=mar,
                        usage_unit="rows",
                        metadata={
                            "connector_id": connector_id,
                            "service_type": service,
                            "group": group_name,
                            "syncs": sync_count,
                            "monthly_active_rows": mar,
                        },
                    ))

        return costs

    def _get_groups(self) -> list[dict]:
        """Get all Fivetran groups (destinations)."""
        resp = httpx.get(
            f"{self.base_url}/groups",
            auth=self._auth(),
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("items", [])

    def _get_connectors(self, group_id: str) -> list[dict]:
        """Get all connectors in a group."""
        resp = httpx.get(
            f"{self.base_url}/groups/{group_id}/connectors",
            auth=self._auth(),
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("items", [])

    def _get_connector_usage(self, connector_id: str, days: int) -> list[dict]:
        """Get usage stats for a connector.

        Tries the usage endpoint; falls back to sync history.
        """
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Try usage/connectors endpoint
        try:
            resp = httpx.get(
                f"{self.base_url}/usage/connectors/{connector_id}",
                auth=self._auth(),
                headers=self._headers(),
                params={
                    "start": start.strftime("%Y-%m-%dT00:00:00Z"),
                    "end": end.strftime("%Y-%m-%dT00:00:00Z"),
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {}).get("usage", [])
        except Exception:
            pass

        # Fallback: get sync history and aggregate by day
        return self._get_sync_history(connector_id, days)

    def _get_sync_history(self, connector_id: str, days: int) -> list[dict]:
        """Get sync history and aggregate into daily usage."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        resp = httpx.get(
            f"{self.base_url}/connectors/{connector_id}/syncs",
            auth=self._auth(),
            headers=self._headers(),
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        syncs = data.get("data", {}).get("items", [])

        # Aggregate by day
        daily = {}
        for sync in syncs:
            created = sync.get("created_at", "")
            if not created:
                continue
            date = created[:10]  # YYYY-MM-DD
            if date < start.strftime("%Y-%m-%d"):
                continue

            if date not in daily:
                daily[date] = {"date": date, "syncs": 0, "monthly_active_rows": 0, "cost": 0.0}
            daily[date]["syncs"] += 1
            daily[date]["monthly_active_rows"] += sync.get("rows_synced", 0)

        return list(daily.values())
