from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

from app.config import settings

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.db_name]


async def create_indexes():
    await db.query_history.create_index(
        [("user_id", ASCENDING), ("end_time", DESCENDING)]
    )
    await db.query_history.create_index(
        [("user_id", ASCENDING), ("warehouse_name", ASCENDING), ("end_time", DESCENDING)]
    )
    await db.query_history.create_index(
        [("user_id", ASCENDING), ("param_hash", ASCENDING)]
    )
    await db.query_history.create_index(
        [("user_id", ASCENDING), ("execution_status", ASCENDING)]
    )
    await db.query_history.create_index(
        [("user_id", ASCENDING), ("query_id", ASCENDING)], unique=True
    )
    await db.query_history.create_index([("query_text", "text")])

    # Unified cost indexes
    await db.unified_costs.create_index(
        [("user_id", ASCENDING), ("date", DESCENDING), ("platform", ASCENDING)]
    )
    await db.unified_costs.create_index(
        [("user_id", ASCENDING), ("platform", ASCENDING), ("resource", ASCENDING)]
    )
    await db.unified_costs.create_index(
        [("user_id", ASCENDING), ("date", ASCENDING),
         ("platform", ASCENDING), ("service", ASCENDING), ("resource", ASCENDING)],
        unique=True,
    )

    # Anomaly indexes
    await db.anomalies.create_index(
        [("user_id", ASCENDING), ("date", DESCENDING)]
    )
    await db.anomalies.create_index(
        [("user_id", ASCENDING), ("date", ASCENDING), ("type", ASCENDING),
         ("scope", ASCENDING), ("platform", ASCENDING), ("resource", ASCENDING)],
        unique=True,
    )

    # Platform connections index
    await db.platform_connections.create_index(
        [("user_id", ASCENDING), ("platform", ASCENDING)]
    )
