"""OpenAI API usage connector.

Pulls token usage and costs from the OpenAI Usage API.
Requires an admin API key from platform.openai.com > Organization Settings.
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector

# Pricing per million tokens (as of 2026)
MODEL_PRICING = {
    "gpt-4.1": {"input": 2.0, "output": 8.0},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.0, "output": 60.0},
    "o1-mini": {"input": 1.10, "output": 4.40},
    "o1-pro": {"input": 150.0, "output": 600.0},
    "o3": {"input": 2.0, "output": 8.0},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "o4-mini": {"input": 1.10, "output": 4.40},
    "dall-e-3": {"input": 0.0, "output": 0.0},  # image pricing is per-image
    "tts-1": {"input": 15.0, "output": 0.0},
    "whisper-1": {"input": 0.006, "output": 0.0},  # per second
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost based on model pricing."""
    pricing = None
    model_lower = model.lower()
    # Sort by key length descending so "gpt-4o-mini" matches before "gpt-4o"
    for key, p in sorted(MODEL_PRICING.items(), key=lambda x: -len(x[0])):
        if key in model_lower:
            pricing = p
            break
    if not pricing:
        # Fallback to gpt-4o pricing
        pricing = {"input": 2.50, "output": 10.0}
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class OpenAIConnector(BaseConnector):
    platform = "openai"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key = credentials["api_key"]
        self.org_id = credentials.get("org_id")
        self.base_url = "https://api.openai.com/v1"

    def test_connection(self) -> dict:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            if self.org_id:
                headers["OpenAI-Organization"] = self.org_id

            resp = httpx.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}

            # Check if the key has admin access to the usage endpoint
            end = datetime.utcnow()
            start = end - timedelta(days=1)
            usage_resp = httpx.get(
                f"{self.base_url}/organization/usage/completions",
                headers=headers,
                params={
                    "start_time": int(start.timestamp()),
                    "end_time": int(end.timestamp()),
                    "bucket_width": "1d",
                },
                timeout=10,
            )
            if usage_resp.status_code == 403:
                return {
                    "success": True,
                    "message": "Connected (note: usage data requires an Admin API key)",
                }
            return {"success": True, "message": "OpenAI API connection successful"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch usage from OpenAI Organization Usage API.

        Uses the /organization/usage endpoint which returns daily
        token usage broken down by model and project.
        """
        costs = []

        try:
            costs = self._fetch_from_usage_api(days)
            if costs:
                return costs
        except Exception:
            pass

        # Try the costs endpoint as fallback
        try:
            costs = self._fetch_from_costs_api(days)
        except Exception:
            pass

        return costs

    def _fetch_from_usage_api(self, days: int) -> list[UnifiedCost]:
        """Fetch from OpenAI's organization usage endpoint."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        if self.org_id:
            headers["OpenAI-Organization"] = self.org_id

        # Completions usage (chat, completions)
        costs = []
        for bucket_type in ["completions", "embeddings"]:
            resp = httpx.get(
                f"{self.base_url}/organization/usage/{bucket_type}",
                headers=headers,
                params={
                    "start_time": int(start.timestamp()),
                    "end_time": int(end.timestamp()),
                    "bucket_width": "1d",
                    "group_by": ["model"],
                },
                timeout=30,
            )

            if resp.status_code != 200:
                continue

            data = resp.json()
            for bucket in data.get("data", []):
                bucket_start = bucket.get("start_time", 0)
                date = datetime.utcfromtimestamp(bucket_start).strftime("%Y-%m-%d")

                for result in bucket.get("results", []):
                    model = result.get("model", "unknown")
                    input_tokens = result.get("input_tokens", 0)
                    output_tokens = result.get("output_tokens", 0)
                    total_tokens = input_tokens + output_tokens

                    cost = _estimate_cost(model, input_tokens, output_tokens)
                    if cost == 0 and total_tokens == 0:
                        continue

                    costs.append(UnifiedCost(
                        date=date,
                        platform="openai",
                        service="openai",
                        resource=model,
                        category=CostCategory.ai_inference,
                        cost_usd=cost,
                        usage_quantity=total_tokens,
                        usage_unit="tokens",
                        metadata={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "model": model,
                            "type": bucket_type,
                        },
                    ))

        return costs

    def _fetch_from_costs_api(self, days: int) -> list[UnifiedCost]:
        """Fallback: fetch from OpenAI's /organization/costs endpoint."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        if self.org_id:
            headers["OpenAI-Organization"] = self.org_id

        resp = httpx.get(
            f"{self.base_url}/organization/costs",
            headers=headers,
            params={
                "start_time": int(start.timestamp()),
                "end_time": int(end.timestamp()),
                "bucket_width": "1d",
                "group_by": ["model"],
            },
            timeout=30,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        costs = []

        for bucket in data.get("data", []):
            bucket_start = bucket.get("start_time", 0)
            date = datetime.utcfromtimestamp(bucket_start).strftime("%Y-%m-%d")

            for result in bucket.get("results", []):
                model = result.get("model", "unknown")
                amount = result.get("amount", {})
                cost_usd = amount.get("value", 0.0)

                if cost_usd == 0:
                    continue

                input_tokens = result.get("input_tokens", 0)
                output_tokens = result.get("output_tokens", 0)

                costs.append(UnifiedCost(
                    date=date,
                    platform="openai",
                    service="openai",
                    resource=model,
                    category=CostCategory.ai_inference,
                    cost_usd=round(cost_usd / 100, 6),  # API returns cents
                    usage_quantity=input_tokens + output_tokens,
                    usage_unit="tokens",
                    metadata={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "model": model,
                    },
                ))

        return costs
