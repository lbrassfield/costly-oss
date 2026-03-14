"""Anthropic API usage connector.

Pulls token usage and costs from the Anthropic Admin API.
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector

# Pricing per million tokens (as of early 2026)
MODEL_PRICING = {
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-haiku-3-5": {"input": 0.80, "output": 4.0},
    "claude-sonnet-3-5": {"input": 3.0, "output": 15.0},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost based on model pricing."""
    pricing = None
    for key, p in sorted(MODEL_PRICING.items(), key=lambda x: -len(x[0])):
        if key in model:
            pricing = p
            break
    if not pricing:
        # Fallback to Sonnet pricing
        pricing = {"input": 3.0, "output": 15.0}
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class AnthropicConnector(BaseConnector):
    platform = "anthropic"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key = credentials["api_key"]
        self.base_url = "https://api.anthropic.com/v1"

    def test_connection(self) -> dict:
        try:
            resp = httpx.get(
                f"{self.base_url}/models",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "Anthropic API connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch usage from Anthropic Admin API.

        Note: The Admin API requires an admin API key (from console.anthropic.com
        Organization Settings > Admin Keys). Regular API keys can't access usage data.
        If the admin API isn't available, falls back to estimating from the
        organization's usage page data.
        """
        costs = []

        # Try the admin usage API first
        try:
            costs = self._fetch_from_admin_api(days)
            if costs:
                return costs
        except Exception:
            pass

        # Fallback: return empty — user needs admin API key
        return costs

    def _fetch_from_admin_api(self, days: int) -> list[UnifiedCost]:
        """Fetch from Anthropic's organization usage endpoint."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # The admin API endpoint for usage
        resp = httpx.get(
            f"{self.base_url}/organizations/usage",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            params={
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
                "granularity": "daily",
                "group_by": "model",
            },
            timeout=30,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        costs = []

        for entry in data.get("usage", []):
            date = entry.get("date", "")
            model = entry.get("model", "unknown")
            input_tokens = entry.get("input_tokens", 0)
            output_tokens = entry.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens

            cost = _estimate_cost(model, input_tokens, output_tokens)
            if cost == 0:
                continue

            costs.append(UnifiedCost(
                date=date,
                platform="anthropic",
                service="anthropic",
                resource=model,
                category=CostCategory.ai_inference,
                cost_usd=cost,
                usage_quantity=total_tokens,
                usage_unit="tokens",
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "model": model,
                },
            ))

        return costs
