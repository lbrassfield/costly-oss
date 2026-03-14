"""Platform pricing engine.

Handles:
1. Market-rate defaults per platform/edition/region
2. User-configurable overrides (negotiated contracts)
3. Full cost decomposition (compute, cloud services, storage, serverless, transfer)
4. Credit price resolution: user override > Snowflake RATE_SHEET_DAILY > edition default

Every platform has opaque billing. This module makes it transparent.
"""

from datetime import datetime

from app.database import db


# ── Snowflake Market Rates ────────────────────────────────────────────────────
# Per-credit prices by edition (on-demand). Capacity contracts are 20-50% less.
# Source: Snowflake pricing page + industry benchmarks as of 2026.

SNOWFLAKE_EDITION_RATES = {
    # edition -> {cloud -> {on_demand, typical_capacity}}
    "standard": {
        "aws": {"on_demand": 2.00, "capacity": 1.60},
        "azure": {"on_demand": 2.00, "capacity": 1.60},
        "gcp": {"on_demand": 2.00, "capacity": 1.60},
    },
    "enterprise": {
        "aws": {"on_demand": 3.00, "capacity": 2.30},
        "azure": {"on_demand": 3.00, "capacity": 2.30},
        "gcp": {"on_demand": 3.00, "capacity": 2.30},
    },
    "business_critical": {
        "aws": {"on_demand": 4.00, "capacity": 3.10},
        "azure": {"on_demand": 4.00, "capacity": 3.10},
        "gcp": {"on_demand": 4.00, "capacity": 3.10},
    },
}

# Snowflake serverless feature credit multipliers (relative to compute credit)
SNOWFLAKE_SERVERLESS_RATES = {
    "snowpipe": 0.06,                # per credit equivalent
    "snowpipe_streaming": 0.05,
    "tasks": 1.0,                    # same as compute
    "materialized_views": 1.0,
    "automatic_clustering": 1.0,
    "search_optimization": 1.0,
    "replication": 1.0,
    "query_acceleration": 1.0,
}

# Snowflake storage rates ($/TB/month)
SNOWFLAKE_STORAGE_RATES = {
    "on_demand": 40.0,
    "capacity": 23.0,
}


# ── Default Market Rates (All Platforms) ──────────────────────────────────────

MARKET_RATES = {
    "snowflake": {
        "description": "Default: Enterprise edition, AWS, capacity pricing",
        "credit_price": 2.30,
        "storage_per_tb_month": 23.0,
        "edition": "enterprise",
        "cloud": "aws",
        "contract": "capacity",
    },
    "aws": {
        "description": "Standard AWS pricing, no EDP discount",
        "edp_discount_pct": 0,
    },
    "dbt_cloud": {
        "description": "dbt Cloud Team plan",
        "plan": "team",
        "price_per_seat_month": 100,
    },
    "openai": {
        "description": "Standard OpenAI API pricing",
        "models": {
            "gpt-4o": {"input": 2.50, "output": 10.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "o3": {"input": 10.0, "output": 40.0},
            "o4-mini": {"input": 1.10, "output": 4.40},
        },
    },
    "anthropic": {
        "description": "Standard Anthropic API pricing",
        "models": {
            "claude-opus-4": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4": {"input": 3.0, "output": 15.0},
            "claude-haiku-3-5": {"input": 0.80, "output": 4.0},
        },
    },
    "databricks": {
        "description": "Standard Databricks DBU pricing",
        "dbu_price": 0.07,  # $/DBU for Jobs Compute
    },
    "fivetran": {
        "description": "Standard Fivetran pricing",
        "plan": "standard",
        "price_per_mar": 0.01,  # per Monthly Active Row
    },
}


# ── Pricing Resolution ────────────────────────────────────────────────────────

async def get_effective_pricing(user_id: str, connection_id: str) -> dict:
    """Get the effective pricing for a connection, merging overrides with defaults."""
    from bson import ObjectId
    conn = await db.platform_connections.find_one({
        "_id": ObjectId(connection_id), "user_id": user_id,
    })
    if not conn:
        return {}

    platform = conn["platform"]
    defaults = MARKET_RATES.get(platform, {})
    overrides = conn.get("pricing_overrides") or {}

    # Deep merge: overrides take precedence
    effective = {**defaults, **overrides}
    effective["_source"] = {
        k: "custom" if k in overrides else "market_default"
        for k in effective if k != "_source"
    }
    effective["platform"] = platform

    return effective


async def get_snowflake_cost_breakdown(user_id: str) -> dict:
    """Get full Snowflake cost decomposition for a user.

    Returns breakdown of:
    - Compute credits (warehouse usage)
    - Cloud services credits
    - Serverless credits (Snowpipe, tasks, clustering, etc.)
    - Storage costs
    - Data transfer costs
    """
    # Get SF connection to find credit price
    sf_conn = await db.snowflake_connections.find_one({
        "user_id": user_id, "is_active": True,
    })

    # Check for pricing override
    platform_conn = await db.platform_connections.find_one({
        "user_id": user_id, "platform": "snowflake",
    })
    overrides = (platform_conn or {}).get("pricing_overrides") or {}
    credit_price = overrides.get("credit_price")

    # If no override, try to get from RATE_SHEET_DAILY (cached in the SF connector)
    if not credit_price and sf_conn:
        from app.services.snowflake import get_credit_price
        credit_price = await get_credit_price(sf_conn)

    # Fallback to enterprise default
    if not credit_price:
        credit_price = MARKET_RATES["snowflake"]["credit_price"]

    storage_rate = overrides.get(
        "storage_per_tb_month",
        MARKET_RATES["snowflake"]["storage_per_tb_month"],
    )

    return {
        "credit_price": credit_price,
        "credit_price_source": "custom" if "credit_price" in overrides else "auto_detected",
        "storage_rate_per_tb": storage_rate,
        "storage_rate_source": "custom" if "storage_per_tb_month" in overrides else "market_default",
        "edition": overrides.get("edition", MARKET_RATES["snowflake"]["edition"]),
        "cloud": overrides.get("cloud", MARKET_RATES["snowflake"]["cloud"]),
        "serverless_rates": SNOWFLAKE_SERVERLESS_RATES,
        "cost_components": [
            {"name": "Compute Credits", "description": "Warehouse runtime (per-second, 60s min)"},
            {"name": "Cloud Services", "description": "Metadata ops, query compilation, login (free up to 10% of compute)"},
            {"name": "Serverless", "description": "Snowpipe, Tasks, Auto-Clustering, Search Optimization"},
            {"name": "Storage", "description": f"Active + Time-Travel + Fail-Safe at ${storage_rate}/TB/month"},
            {"name": "Data Transfer", "description": "Cross-region and cross-cloud egress"},
        ],
    }


# ── Pricing config API helpers ────────────────────────────────────────────────

def get_platform_pricing_template(platform: str) -> dict:
    """Return the configurable pricing fields for a platform."""
    templates = {
        "snowflake": {
            "fields": [
                {"key": "credit_price", "label": "Credit Price ($/credit)", "type": "number",
                 "default": 2.30, "help": "Your negotiated per-credit rate. Check your Snowflake contract or RATE_SHEET_DAILY view."},
                {"key": "storage_per_tb_month", "label": "Storage Rate ($/TB/month)", "type": "number",
                 "default": 23.0, "help": "On-demand: ~$40/TB, Capacity: ~$23/TB"},
                {"key": "edition", "label": "Edition", "type": "select",
                 "options": ["standard", "enterprise", "business_critical"], "default": "enterprise"},
                {"key": "cloud", "label": "Cloud Provider", "type": "select",
                 "options": ["aws", "azure", "gcp"], "default": "aws"},
                {"key": "contract", "label": "Contract Type", "type": "select",
                 "options": ["on_demand", "capacity"], "default": "capacity"},
            ],
        },
        "aws": {
            "fields": [
                {"key": "edp_discount_pct", "label": "EDP Discount (%)", "type": "number",
                 "default": 0, "help": "Enterprise Discount Program percentage (e.g. 10 for 10% off)"},
                {"key": "savings_plan_coverage_pct", "label": "Savings Plan Coverage (%)", "type": "number",
                 "default": 0, "help": "Percentage of compute covered by Savings Plans"},
            ],
        },
        "openai": {
            "fields": [
                {"key": "discount_pct", "label": "Volume Discount (%)", "type": "number",
                 "default": 0, "help": "Negotiated volume discount percentage"},
            ],
            "per_model": True,
            "model_fields": [
                {"key": "input", "label": "Input ($/1M tokens)", "type": "number"},
                {"key": "output", "label": "Output ($/1M tokens)", "type": "number"},
            ],
        },
        "anthropic": {
            "fields": [
                {"key": "discount_pct", "label": "Volume Discount (%)", "type": "number",
                 "default": 0, "help": "Negotiated volume discount percentage"},
            ],
            "per_model": True,
            "model_fields": [
                {"key": "input", "label": "Input ($/1M tokens)", "type": "number"},
                {"key": "output", "label": "Output ($/1M tokens)", "type": "number"},
            ],
        },
        "databricks": {
            "fields": [
                {"key": "dbu_price", "label": "DBU Price ($/DBU)", "type": "number",
                 "default": 0.07, "help": "Your contracted $/DBU rate for Jobs Compute"},
                {"key": "discount_pct", "label": "Committed Use Discount (%)", "type": "number",
                 "default": 0},
            ],
        },
        "fivetran": {
            "fields": [
                {"key": "plan", "label": "Plan", "type": "select",
                 "options": ["free", "standard", "enterprise", "business_critical"], "default": "standard"},
                {"key": "discount_pct", "label": "Discount (%)", "type": "number", "default": 0},
            ],
        },
    }
    return templates.get(platform, {"fields": [
        {"key": "discount_pct", "label": "Discount (%)", "type": "number",
         "default": 0, "help": "Flat percentage discount"},
    ]})
