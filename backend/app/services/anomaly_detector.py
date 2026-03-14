"""Anomaly detection engine for unified cost data.

Strategies:
1. Z-score spike detection — flags days where cost > mean + 2*stddev
2. Day-over-day change — flags >50% increase from previous day
3. Week-over-week change — flags >30% increase vs same day last week
4. Resource-level spikes — flags individual resources with unusual cost

Anomalies are stored in the `anomalies` collection and surfaced via API.
"""

import math
from datetime import datetime, timedelta

from app.database import db


# ── Thresholds ────────────────────────────────────────────────────────────────

ZSCORE_THRESHOLD = 2.0          # Standard deviations above mean
DOD_SPIKE_PCT = 0.50            # 50% day-over-day increase
WOW_SPIKE_PCT = 0.30            # 30% week-over-week increase
MIN_COST_FOR_ALERT = 5.0        # Ignore anomalies below $5/day
LOOKBACK_DAYS = 30              # Rolling window for baseline


# ── Core detection ────────────────────────────────────────────────────────────

async def detect_anomalies_for_user(user_id: str) -> list[dict]:
    """Run all anomaly detection strategies for a single user.
    Returns list of detected anomalies (also persisted to DB).
    """
    since = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS + 7)).strftime("%Y-%m-%d")

    # Get daily costs by platform
    daily_by_platform = await db.unified_costs.aggregate([
        {"$match": {"user_id": user_id, "date": {"$gte": since}}},
        {"$group": {
            "_id": {"date": "$date", "platform": "$platform"},
            "cost": {"$sum": "$cost_usd"},
        }},
        {"$sort": {"_id.date": 1}},
    ]).to_list(5000)

    # Get daily totals
    daily_totals = await db.unified_costs.aggregate([
        {"$match": {"user_id": user_id, "date": {"$gte": since}}},
        {"$group": {
            "_id": "$date",
            "cost": {"$sum": "$cost_usd"},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(365)

    # Get daily costs by resource (top spenders only)
    daily_by_resource = await db.unified_costs.aggregate([
        {"$match": {"user_id": user_id, "date": {"$gte": since}}},
        {"$group": {
            "_id": {"date": "$date", "platform": "$platform", "resource": "$resource"},
            "cost": {"$sum": "$cost_usd"},
        }},
        {"$sort": {"_id.date": 1}},
    ]).to_list(10000)

    anomalies = []

    # 1. Z-score on total daily spend
    anomalies.extend(_zscore_anomalies(daily_totals, user_id, scope="total"))

    # 2. Z-score per platform
    platforms = set(r["_id"]["platform"] for r in daily_by_platform)
    for platform in platforms:
        platform_daily = [
            {"_id": r["_id"]["date"], "cost": r["cost"]}
            for r in daily_by_platform if r["_id"]["platform"] == platform
        ]
        anomalies.extend(
            _zscore_anomalies(platform_daily, user_id, scope="platform", platform=platform)
        )

    # 3. Day-over-day spikes on total
    anomalies.extend(_dod_anomalies(daily_totals, user_id))

    # 4. Week-over-week spikes on total
    anomalies.extend(_wow_anomalies(daily_totals, user_id))

    # 5. Resource-level spikes
    resources = set(
        (r["_id"]["platform"], r["_id"]["resource"])
        for r in daily_by_resource
    )
    for platform, resource in resources:
        resource_daily = [
            {"_id": r["_id"]["date"], "cost": r["cost"]}
            for r in daily_by_resource
            if r["_id"]["platform"] == platform and r["_id"]["resource"] == resource
        ]
        if len(resource_daily) < 5:
            continue
        avg_cost = sum(r["cost"] for r in resource_daily) / len(resource_daily)
        if avg_cost < MIN_COST_FOR_ALERT:
            continue
        anomalies.extend(
            _zscore_anomalies(
                resource_daily, user_id,
                scope="resource", platform=platform, resource=resource,
            )
        )

    # Deduplicate and persist
    if anomalies:
        await _persist_anomalies(user_id, anomalies)

    return anomalies


def _zscore_anomalies(
    daily: list[dict], user_id: str,
    scope: str = "total", platform: str = "", resource: str = "",
) -> list[dict]:
    """Detect anomalies using z-score on daily cost series."""
    if len(daily) < 7:
        return []

    costs = [r["cost"] for r in daily]
    mean = sum(costs) / len(costs)
    if mean < MIN_COST_FOR_ALERT:
        return []

    variance = sum((c - mean) ** 2 for c in costs) / len(costs)
    stddev = math.sqrt(variance)
    if stddev == 0:
        return []

    anomalies = []
    # Only check the last 7 days for new anomalies
    recent = daily[-7:]
    for entry in recent:
        cost = entry["cost"]
        zscore = (cost - mean) / stddev
        if zscore >= ZSCORE_THRESHOLD:
            anomalies.append({
                "user_id": user_id,
                "date": entry["_id"],
                "type": "zscore_spike",
                "severity": "high" if zscore >= 3.0 else "medium",
                "scope": scope,
                "platform": platform,
                "resource": resource,
                "cost": round(cost, 2),
                "baseline_mean": round(mean, 2),
                "baseline_stddev": round(stddev, 2),
                "zscore": round(zscore, 2),
                "message": _build_message(
                    scope, platform, resource, cost, mean, zscore,
                ),
                "detected_at": datetime.utcnow().isoformat(),
                "acknowledged": False,
            })
    return anomalies


def _dod_anomalies(daily: list[dict], user_id: str) -> list[dict]:
    """Detect day-over-day cost spikes."""
    if len(daily) < 2:
        return []

    anomalies = []
    for i in range(max(1, len(daily) - 7), len(daily)):
        prev = daily[i - 1]["cost"]
        curr = daily[i]["cost"]
        if prev < MIN_COST_FOR_ALERT:
            continue
        pct_change = (curr - prev) / prev
        if pct_change >= DOD_SPIKE_PCT:
            anomalies.append({
                "user_id": user_id,
                "date": daily[i]["_id"],
                "type": "day_over_day_spike",
                "severity": "high" if pct_change >= 1.0 else "medium",
                "scope": "total",
                "platform": "",
                "resource": "",
                "cost": round(curr, 2),
                "previous_cost": round(prev, 2),
                "pct_change": round(pct_change * 100, 1),
                "message": (
                    f"Total spend spiked {pct_change * 100:.0f}% day-over-day: "
                    f"${curr:.0f} vs ${prev:.0f} previous day"
                ),
                "detected_at": datetime.utcnow().isoformat(),
                "acknowledged": False,
            })
    return anomalies


def _wow_anomalies(daily: list[dict], user_id: str) -> list[dict]:
    """Detect week-over-week cost spikes (same day last week)."""
    if len(daily) < 8:
        return []

    date_to_cost = {r["_id"]: r["cost"] for r in daily}
    anomalies = []

    for entry in daily[-7:]:
        date_str = entry["_id"]
        curr = entry["cost"]
        # Find same day last week
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            week_ago = (dt - timedelta(days=7)).strftime("%Y-%m-%d")
        except ValueError:
            continue

        prev = date_to_cost.get(week_ago)
        if prev is None or prev < MIN_COST_FOR_ALERT:
            continue

        pct_change = (curr - prev) / prev
        if pct_change >= WOW_SPIKE_PCT:
            anomalies.append({
                "user_id": user_id,
                "date": date_str,
                "type": "week_over_week_spike",
                "severity": "high" if pct_change >= 0.75 else "medium",
                "scope": "total",
                "platform": "",
                "resource": "",
                "cost": round(curr, 2),
                "previous_cost": round(prev, 2),
                "pct_change": round(pct_change * 100, 1),
                "message": (
                    f"Total spend up {pct_change * 100:.0f}% week-over-week: "
                    f"${curr:.0f} vs ${prev:.0f} same day last week"
                ),
                "detected_at": datetime.utcnow().isoformat(),
                "acknowledged": False,
            })
    return anomalies


def _build_message(
    scope: str, platform: str, resource: str,
    cost: float, mean: float, zscore: float,
) -> str:
    """Build a human-readable anomaly message."""
    pct_above = ((cost - mean) / mean * 100) if mean > 0 else 0
    if scope == "total":
        return (
            f"Total daily spend of ${cost:.0f} is {pct_above:.0f}% above "
            f"the {LOOKBACK_DAYS}-day average of ${mean:.0f} (z-score: {zscore:.1f})"
        )
    if scope == "platform":
        return (
            f"{platform} spend of ${cost:.0f} is {pct_above:.0f}% above "
            f"its {LOOKBACK_DAYS}-day average of ${mean:.0f} (z-score: {zscore:.1f})"
        )
    return (
        f"{platform}/{resource} cost of ${cost:.0f} is {pct_above:.0f}% above "
        f"its average of ${mean:.0f} (z-score: {zscore:.1f})"
    )


# ── Persistence ───────────────────────────────────────────────────────────────

async def _persist_anomalies(user_id: str, anomalies: list[dict]):
    """Upsert anomalies — deduplicate by user+date+type+scope+platform+resource."""
    from pymongo import UpdateOne

    ops = []
    for a in anomalies:
        key = {
            "user_id": user_id,
            "date": a["date"],
            "type": a["type"],
            "scope": a["scope"],
            "platform": a["platform"],
            "resource": a["resource"],
        }
        ops.append(UpdateOne(key, {"$set": a}, upsert=True))

    if ops:
        result = await db.anomalies.bulk_write(ops)
        new = result.upserted_count
        if new > 0:
            print(f"[ANOMALY] {new} new anomalies detected for user {user_id[:8]}...")


async def detect_anomalies_all_users():
    """Run anomaly detection for all users with cost data."""
    user_ids = await db.unified_costs.distinct("user_id")
    total = 0
    for user_id in user_ids:
        try:
            anomalies = await detect_anomalies_for_user(user_id)
            total += len(anomalies)
        except Exception as e:
            print(f"[ANOMALY] Error for user {user_id[:8]}...: {e}")
    print(f"[ANOMALY] Detection complete. {total} anomalies across {len(user_ids)} users.")


# ── API helpers ───────────────────────────────────────────────────────────────

async def get_anomalies(user_id: str, days: int = 30, acknowledged: bool | None = None) -> list[dict]:
    """Get anomalies for a user, optionally filtered."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    query: dict = {"user_id": user_id, "date": {"$gte": since}}
    if acknowledged is not None:
        query["acknowledged"] = acknowledged

    cursor = db.anomalies.find(query).sort("date", -1)
    results = await cursor.to_list(200)
    for r in results:
        r["_id"] = str(r["_id"])
    return results


async def acknowledge_anomaly(user_id: str, anomaly_id: str) -> bool:
    """Mark an anomaly as acknowledged."""
    from bson import ObjectId
    result = await db.anomalies.update_one(
        {"_id": ObjectId(anomaly_id), "user_id": user_id},
        {"$set": {"acknowledged": True, "acknowledged_at": datetime.utcnow().isoformat()}},
    )
    return result.modified_count > 0
