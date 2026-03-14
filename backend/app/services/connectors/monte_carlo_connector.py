"""Monte Carlo data observability connector.

Pulls monitoring usage from Monte Carlo's GraphQL API.
Tracks tables monitored, incidents, and data quality costs.
Credentials: api_key_id + api_token (from Monte Carlo Settings > API Keys).
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector


class MonteCarloConnector(BaseConnector):
    platform = "monte_carlo"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key_id = credentials["api_key_id"]
        self.api_token = credentials["api_token"]
        self.base_url = "https://api.getmontecarlo.com/graphql"

    def _headers(self) -> dict:
        return {
            "x-mcd-id": self.api_key_id,
            "x-mcd-token": self.api_token,
            "Content-Type": "application/json",
        }

    def test_connection(self) -> dict:
        try:
            resp = httpx.post(
                self.base_url,
                headers=self._headers(),
                json={"query": "{ getUser { email } }"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data", {}).get("getUser"):
                    return {"success": True, "message": "Monte Carlo connection successful"}
                if data.get("errors"):
                    return {"success": False, "message": data["errors"][0].get("message", "Auth failed")}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch Monte Carlo usage as cost records.

        Monte Carlo pricing is typically flat per tables monitored.
        We track usage metrics (monitors, incidents, tables) to
        attribute cost and surface data quality spend.
        """
        costs = []

        # Get monitored tables count and incidents
        try:
            tables_data = self._get_tables_monitored()
            incidents_data = self._get_incidents(days)
        except Exception:
            return costs

        # Monte Carlo pricing: ~$40-80/table/month for Scale plan
        # We use $50/table/month as default estimate
        table_count = tables_data.get("count", 0)
        monthly_cost = table_count * 50.0
        daily_cost = round(monthly_cost / 30, 4)

        if daily_cost == 0:
            return costs

        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Create daily records
        current = start
        while current < end:
            date = current.strftime("%Y-%m-%d")

            # Count incidents for this day
            day_incidents = sum(
                1 for inc in incidents_data
                if inc.get("date", "")[:10] == date
            )

            costs.append(UnifiedCost(
                date=date,
                platform="monte_carlo",
                service="monte_carlo",
                resource="data_observability",
                category=CostCategory.data_quality,
                cost_usd=daily_cost,
                usage_quantity=table_count,
                usage_unit="tables",
                metadata={
                    "tables_monitored": table_count,
                    "incidents": day_incidents,
                },
            ))

            current += timedelta(days=1)

        return costs

    def _get_tables_monitored(self) -> dict:
        """Get count of tables being monitored."""
        query = """
        {
            getTablesMonitoredInfo {
                totalTables
                monitoredTables
            }
        }
        """
        resp = httpx.post(
            self.base_url,
            headers=self._headers(),
            json={"query": query},
            timeout=15,
        )
        if resp.status_code != 200:
            return {"count": 0}

        data = resp.json()
        info = data.get("data", {}).get("getTablesMonitoredInfo", {})
        return {"count": info.get("monitoredTables", 0)}

    def _get_incidents(self, days: int) -> list[dict]:
        """Get recent incidents."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        query = """
        query getIncidents($startTime: DateTime, $endTime: DateTime) {
            getIncidents(
                startTime: $startTime
                endTime: $endTime
                first: 500
            ) {
                edges {
                    node {
                        id
                        createdTime
                        severity
                        incidentType
                    }
                }
            }
        }
        """
        resp = httpx.post(
            self.base_url,
            headers=self._headers(),
            json={
                "query": query,
                "variables": {
                    "startTime": start.isoformat() + "Z",
                    "endTime": end.isoformat() + "Z",
                },
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        edges = data.get("data", {}).get("getIncidents", {}).get("edges", [])
        return [
            {"date": e["node"].get("createdTime", ""), "severity": e["node"].get("severity")}
            for e in edges
            if e.get("node")
        ]
