CREDITS_MAP = {
    "X-Small": 1, "Small": 2, "Medium": 4, "Large": 8, "X-Large": 16,
    "2X-Large": 32, "3X-Large": 64, "4X-Large": 128, "5X-Large": 256, "6X-Large": 512,
    # alternate casings from SHOW WAREHOUSES
    "XSMALL": 1, "SMALL": 2, "MEDIUM": 4, "LARGE": 8, "XLARGE": 16,
    "2XLARGE": 32, "3XLARGE": 64, "4XLARGE": 128, "X-SMALL": 1,
}

CACHE_TTL = {
    "dashboard": 900,       # 15 min
    "costs": 1800,          # 30 min
    "queries": 900,         # 15 min
    "workloads": 900,       # 15 min
    "storage": 3600,        # 1 hr
    "warehouses": 1800,     # 30 min
    "credit_price": 86400,  # 24 hr
    "recommendations": 1800,  # 30 min
    "warehouse_sizing": 1800,  # 30 min
    "autosuspend": 1800,       # 30 min
    "spillage": 1800,          # 30 min
    "query_patterns": 900,     # 15 min
    "cost_attribution": 1800,  # 30 min
    "stale_tables": 3600,      # 1 hr
}

VALID_WAREHOUSE_SIZES = [
    "XSMALL", "SMALL", "MEDIUM", "LARGE", "XLARGE",
    "2XLARGE", "3XLARGE", "4XLARGE", "5XLARGE", "6XLARGE",
    "X-SMALL", "X-LARGE", "2X-LARGE", "3X-LARGE", "4X-LARGE", "5X-LARGE", "6X-LARGE",
]
