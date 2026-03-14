"""BigQuery connector.

Pulls query costs from BigQuery INFORMATION_SCHEMA.JOBS or GCP Billing API.
Credentials: GCP service account JSON with BigQuery Data Viewer + Job User roles.
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector

# BigQuery pricing (on-demand)
BQ_COST_PER_TB = 6.25  # $6.25 per TB scanned (as of 2026)


class BigQueryConnector(BaseConnector):
    platform = "gcp"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.project_id = credentials["project_id"]
        self.service_account = credentials.get("service_account_json")

    def _get_access_token(self) -> str:
        """Get OAuth2 access token from service account."""
        import json
        import time

        if isinstance(self.service_account, str):
            sa = json.loads(self.service_account)
        else:
            sa = self.service_account

        try:
            from google.oauth2 import service_account as sa_module
            from google.auth.transport.requests import Request

            creds = sa_module.Credentials.from_service_account_info(
                sa,
                scopes=["https://www.googleapis.com/auth/bigquery.readonly",
                        "https://www.googleapis.com/auth/cloud-platform"],
            )
            creds.refresh(Request())
            return creds.token
        except ImportError:
            pass

        # Manual JWT flow
        import jwt as pyjwt

        now = int(time.time())
        payload = {
            "iss": sa["client_email"],
            "scope": "https://www.googleapis.com/auth/bigquery.readonly https://www.googleapis.com/auth/cloud-platform",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }

        signed_jwt = pyjwt.encode(payload, sa["private_key"], algorithm="RS256")

        resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_jwt,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def test_connection(self) -> dict:
        try:
            token = self._get_access_token()
            resp = httpx.get(
                f"https://bigquery.googleapis.com/bigquery/v2/projects/{self.project_id}/datasets",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "BigQuery connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch BigQuery costs from INFORMATION_SCHEMA.JOBS.

        Queries the jobs metadata to calculate bytes billed and
        estimate costs based on on-demand pricing.
        """
        try:
            token = self._get_access_token()
        except Exception:
            return []

        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Query INFORMATION_SCHEMA.JOBS for bytes billed
        query = f"""
        SELECT
            DATE(creation_time) as job_date,
            user_email,
            project_id,
            SUM(total_bytes_billed) as total_bytes_billed,
            SUM(total_slot_ms) as total_slot_ms,
            COUNT(*) as job_count
        FROM `region-us`.INFORMATION_SCHEMA.JOBS
        WHERE creation_time >= TIMESTAMP('{start.strftime("%Y-%m-%d")}')
          AND creation_time < TIMESTAMP('{end.strftime("%Y-%m-%d")}')
          AND state = 'DONE'
          AND statement_type IS NOT NULL
        GROUP BY job_date, user_email, project_id
        ORDER BY job_date
        """

        resp = httpx.post(
            f"https://bigquery.googleapis.com/bigquery/v2/projects/{self.project_id}/queries",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "useLegacySql": False,
                "timeoutMs": 30000,
            },
            timeout=60,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        rows = data.get("rows", [])
        schema = data.get("schema", {}).get("fields", [])

        costs = []
        for row in rows:
            values = [cell.get("v") for cell in row.get("f", [])]
            if len(values) < 6:
                continue

            date = values[0]
            user = values[1] or "unknown"
            project = values[2] or self.project_id
            bytes_billed = int(values[3] or 0)
            slot_ms = int(values[4] or 0)
            job_count = int(values[5] or 0)

            # Cost = bytes billed / 1TB * price per TB
            tb_scanned = bytes_billed / (1024 ** 4)
            cost = round(tb_scanned * BQ_COST_PER_TB, 4)

            if cost == 0 and bytes_billed == 0:
                continue

            costs.append(UnifiedCost(
                date=date,
                platform="gcp",
                service="bigquery",
                resource=f"{project}/{user}",
                category=CostCategory.compute,
                cost_usd=cost,
                usage_quantity=round(tb_scanned, 6),
                usage_unit="TB_scanned",
                metadata={
                    "bytes_billed": bytes_billed,
                    "slot_ms": slot_ms,
                    "job_count": job_count,
                    "user": user,
                    "project": project,
                },
            ))

        # Also get storage costs
        storage_costs = self._fetch_storage_costs(token, start, end)
        costs.extend(storage_costs)

        return costs

    def _fetch_storage_costs(self, token: str, start: datetime, end: datetime) -> list[UnifiedCost]:
        """Fetch BigQuery storage costs from TABLE_STORAGE."""
        query = f"""
        SELECT
            DATE('{end.strftime("%Y-%m-%d")}') as snapshot_date,
            table_schema as dataset,
            SUM(total_logical_bytes) as logical_bytes,
            SUM(total_physical_bytes) as physical_bytes
        FROM `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
        GROUP BY dataset
        """

        resp = httpx.post(
            f"https://bigquery.googleapis.com/bigquery/v2/projects/{self.project_id}/queries",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "useLegacySql": False,
                "timeoutMs": 30000,
            },
            timeout=60,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        costs = []
        # BQ storage: $0.02/GB/month for active, $0.01/GB/month for long-term
        for row in data.get("rows", []):
            values = [cell.get("v") for cell in row.get("f", [])]
            if len(values) < 4:
                continue

            date = values[0]
            dataset = values[1] or "unknown"
            logical_gb = int(values[2] or 0) / (1024 ** 3)
            physical_gb = int(values[3] or 0) / (1024 ** 3)

            daily_cost = round((logical_gb * 0.02) / 30, 4)
            if daily_cost == 0:
                continue

            costs.append(UnifiedCost(
                date=date,
                platform="gcp",
                service="bigquery_storage",
                resource=f"{self.project_id}/{dataset}",
                category=CostCategory.storage,
                cost_usd=daily_cost,
                usage_quantity=round(logical_gb, 2),
                usage_unit="GB",
                metadata={
                    "dataset": dataset,
                    "logical_gb": round(logical_gb, 2),
                    "physical_gb": round(physical_gb, 2),
                },
            ))

        return costs
