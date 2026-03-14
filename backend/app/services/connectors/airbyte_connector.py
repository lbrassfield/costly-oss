"""Airbyte connector.

Pulls sync usage and costs from Airbyte Cloud API.
For self-hosted Airbyte, tracks sync volume from the API.
Credentials: api_token (from Airbyte Cloud Settings > API Tokens)
             or host + api_token for self-hosted.
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector


class AirbyteConnector(BaseConnector):
    platform = "airbyte"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_token = credentials["api_token"]
        # Cloud vs self-hosted
        self.base_url = credentials.get("host", "https://api.airbyte.com/v1")
        self.is_cloud = "api.airbyte.com" in self.base_url

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }

    def test_connection(self) -> dict:
        try:
            resp = httpx.get(
                f"{self.base_url}/workspaces",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "Airbyte connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch sync jobs and aggregate into daily cost records."""
        costs = []

        try:
            connections = self._get_connections()
        except Exception:
            return costs

        end = datetime.utcnow()
        start = end - timedelta(days=days)

        for conn in connections:
            connection_id = conn.get("connectionId", "")
            name = conn.get("name", connection_id)
            source_name = conn.get("source", {}).get("name", "unknown")
            dest_name = conn.get("destination", {}).get("name", "unknown")

            try:
                jobs = self._get_jobs(connection_id, start)
            except Exception:
                continue

            # Aggregate by day
            daily = {}
            for job in jobs:
                created = job.get("startTime", job.get("createdAt", ""))
                if not created:
                    continue
                date = created[:10]
                if date < start.strftime("%Y-%m-%d"):
                    continue

                if date not in daily:
                    daily[date] = {"bytes": 0, "records": 0, "duration_s": 0, "syncs": 0}

                daily[date]["bytes"] += job.get("bytesSynced", 0)
                daily[date]["records"] += job.get("rowsSynced", 0)
                daily[date]["syncs"] += 1
                daily[date]["duration_s"] += job.get("duration", 0)

            for date, stats in daily.items():
                # Airbyte Cloud pricing: ~$15 per 1M records (varies by plan)
                records = stats["records"]
                if self.is_cloud:
                    cost = round((records / 1_000_000) * 15.0, 4) if records > 0 else 0
                else:
                    cost = 0  # Self-hosted — no per-record cost

                if cost == 0 and records == 0:
                    continue

                costs.append(UnifiedCost(
                    date=date,
                    platform="airbyte",
                    service=f"airbyte_{source_name.lower().replace(' ', '_')}",
                    resource=name,
                    category=CostCategory.ingestion,
                    cost_usd=cost,
                    usage_quantity=records,
                    usage_unit="records",
                    metadata={
                        "source": source_name,
                        "destination": dest_name,
                        "bytes_synced": stats["bytes"],
                        "syncs": stats["syncs"],
                        "duration_seconds": stats["duration_s"],
                    },
                ))

        return costs

    def _get_connections(self) -> list[dict]:
        """Get all Airbyte connections."""
        resp = httpx.get(
            f"{self.base_url}/connections",
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", data.get("connections", []))

    def _get_jobs(self, connection_id: str, since: datetime) -> list[dict]:
        """Get sync jobs for a connection."""
        resp = httpx.get(
            f"{self.base_url}/jobs",
            headers=self._headers(),
            params={
                "connectionId": connection_id,
                "status": "succeeded",
                "createdAtStart": since.strftime("%Y-%m-%dT00:00:00Z"),
                "limit": 100,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("data", data.get("jobs", []))
