"""Scheduled cost sync — pulls costs from all connected platforms and persists
them into the unified_costs collection.

Runs every 6 hours via APScheduler. Each sync:
1. Iterates all users with platform_connections
2. For each connection, fetches costs via the connector
3. Upserts into unified_costs (deduped by user+date+platform+service+resource)
4. Runs anomaly detection on the freshly synced data
"""

from datetime import datetime

from app.database import db
from app.services.unified_costs import sync_platform_costs


async def sync_all_platform_costs():
    """Sync cost data for every user's connected platforms."""
    print(f"[COST SYNC] Starting full platform cost sync at {datetime.utcnow().isoformat()}")

    try:
        # Get all unique user_ids with platform connections
        user_ids = await db.platform_connections.distinct("user_id")
        if not user_ids:
            print("[COST SYNC] No platform connections found, skipping.")
            return

        total_synced = 0
        total_errors = 0

        for user_id in user_ids:
            connections = await db.platform_connections.find(
                {"user_id": user_id}
            ).to_list(100)

            for conn in connections:
                conn_id = str(conn["_id"])
                platform = conn.get("platform", "unknown")
                try:
                    result = await sync_platform_costs(user_id, conn_id, days=30)
                    records = result.get("records", 0)
                    total_synced += records
                    if records > 0:
                        print(f"[COST SYNC] {platform} for user {user_id[:8]}...: {records} records")
                except Exception as e:
                    total_errors += 1
                    print(f"[COST SYNC] Error syncing {platform} for user {user_id[:8]}...: {e}")

        # Run anomaly detection after sync
        try:
            from app.services.anomaly_detector import detect_anomalies_all_users
            await detect_anomalies_all_users()
        except Exception as e:
            print(f"[COST SYNC] Anomaly detection error: {e}")

        print(
            f"[COST SYNC] Complete. {total_synced} records synced, "
            f"{total_errors} errors, {len(user_ids)} users."
        )

    except Exception as e:
        print(f"[COST SYNC] Fatal error: {e}")
