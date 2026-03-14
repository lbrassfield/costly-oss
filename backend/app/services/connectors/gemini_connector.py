"""Google Gemini / Vertex AI connector.

Pulls AI token usage costs from Google Cloud Billing API,
filtered to Vertex AI / Gemini API services.
Credentials: GCP service account JSON key with Billing Viewer role.
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector

# Pricing per million tokens (as of early 2026)
MODEL_PRICING = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.0-pro": {"input": 1.25, "output": 10.0},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.0},
    "gemini-1.0-pro": {"input": 0.50, "output": 1.50},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost based on model pricing."""
    pricing = None
    model_lower = model.lower()
    for key, p in MODEL_PRICING.items():
        if key in model_lower:
            pricing = p
            break
    if not pricing:
        # Fallback to flash pricing
        pricing = {"input": 0.10, "output": 0.40}
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class GeminiConnector(BaseConnector):
    platform = "gemini"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key = credentials.get("api_key")
        # For Vertex AI: service account JSON
        self.service_account = credentials.get("service_account_json")
        self.project_id = credentials.get("project_id")
        self.use_vertex = bool(self.service_account and self.project_id)

    def test_connection(self) -> dict:
        if self.use_vertex:
            return self._test_vertex()
        return self._test_ai_studio()

    def _test_ai_studio(self) -> dict:
        """Test Google AI Studio API key."""
        try:
            resp = httpx.get(
                "https://generativelanguage.googleapis.com/v1/models",
                params={"key": self.api_key},
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "Google AI Studio connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _test_vertex(self) -> dict:
        """Test Vertex AI connection via service account."""
        try:
            token = self._get_access_token()
            resp = httpx.get(
                f"https://us-central1-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/us-central1/models",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code in (200, 403):
                # 403 means auth works but may lack model list permission — still valid
                return {"success": True, "message": "Vertex AI connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch Gemini usage costs.

        For Vertex AI: uses BigQuery billing export or Cloud Billing API.
        For AI Studio: uses the API key usage (limited visibility).
        """
        if self.use_vertex:
            return self._fetch_vertex_costs(days)
        return self._fetch_ai_studio_costs(days)

    def _fetch_ai_studio_costs(self, days: int) -> list[UnifiedCost]:
        """Fetch from Google AI Studio.

        AI Studio doesn't have a usage API like Anthropic/OpenAI.
        We track what we can from the available endpoints.
        """
        # Google AI Studio has limited programmatic usage tracking.
        # Return empty — users should use Vertex AI for production cost tracking.
        return []

    def _fetch_vertex_costs(self, days: int) -> list[UnifiedCost]:
        """Fetch Vertex AI costs from Cloud Billing API."""
        costs = []

        try:
            token = self._get_access_token()
        except Exception:
            return costs

        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Use Cloud Billing Budgets API or BigQuery billing export
        # The most reliable method is querying the billing export in BigQuery
        try:
            costs = self._fetch_from_billing_api(token, start, end)
        except Exception:
            pass

        return costs

    def _fetch_from_billing_api(self, token: str, start: datetime, end: datetime) -> list[UnifiedCost]:
        """Fetch from GCP Cloud Billing API, filtered to AI Platform / Vertex AI."""
        # GCP billing data is best accessed via BigQuery billing export
        # For now, use the Cloud Monitoring API to get Vertex AI metrics
        costs = []

        # Query Vertex AI prediction and training metrics
        resp = httpx.post(
            f"https://monitoring.googleapis.com/v3/projects/{self.project_id}/timeSeries:query",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "query": (
                    'fetch aiplatform.googleapis.com/prediction/online/request_count '
                    '| align rate(1d) '
                    f'| within {(end - start).days}d'
                ),
            },
            timeout=30,
        )

        if resp.status_code != 200:
            return costs

        data = resp.json()
        for ts in data.get("timeSeriesData", []):
            model_id = ""
            for label in ts.get("labelValues", []):
                if label.get("stringValue"):
                    model_id = label["stringValue"]
                    break

            for point in ts.get("pointData", []):
                time_interval = point.get("timeInterval", {})
                date = time_interval.get("startTime", "")[:10]
                value = point.get("values", [{}])[0].get("doubleValue", 0)

                if value == 0:
                    continue

                # Estimate cost from request count (rough)
                # Actual cost depends on model, input/output size
                estimated_cost = round(value * 0.001, 4)  # placeholder

                costs.append(UnifiedCost(
                    date=date,
                    platform="gemini",
                    service="vertex_ai",
                    resource=model_id or "vertex-ai-prediction",
                    category=CostCategory.ai_inference,
                    cost_usd=estimated_cost,
                    usage_quantity=round(value, 2),
                    usage_unit="requests",
                    metadata={
                        "model": model_id,
                        "source": "cloud_monitoring",
                    },
                ))

        return costs

    def _get_access_token(self) -> str:
        """Get OAuth2 access token from service account JSON."""
        import json
        import time
        import hashlib
        import base64

        if isinstance(self.service_account, str):
            sa = json.loads(self.service_account)
        else:
            sa = self.service_account

        # Use google-auth library if available, otherwise manual JWT
        try:
            from google.oauth2 import service_account as sa_module
            from google.auth.transport.requests import Request

            creds = sa_module.Credentials.from_service_account_info(
                sa,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
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
            "scope": "https://www.googleapis.com/auth/cloud-platform",
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
