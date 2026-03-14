from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import db
from app.deps import get_current_admin_user
from app.services.snowflake import sync_recommendations
from app.utils.helpers import run_in_thread

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(_: str = Depends(get_current_admin_user)):
    now = datetime.utcnow()
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    total_users = await db.users.count_documents({})
    total_connections = await db.snowflake_connections.count_documents({})
    total_queries = await db.query_history.count_documents({})
    recent_signups = await db.users.count_documents({"created_at": {"$gte": seven_days_ago}})

    return {
        "total_users": total_users,
        "total_connections": total_connections,
        "total_queries": total_queries,
        "recent_signups": recent_signups,
    }


@router.get("/users")
async def admin_users(_: str = Depends(get_current_admin_user)):
    users = await db.users.find(
        {}, {"password_hash": 0, "_id": 0}
    ).sort("created_at", -1).to_list(length=1000)

    user_ids = [u["user_id"] for u in users]

    # Count connections per user
    conn_pipeline = [
        {"$match": {"user_id": {"$in": user_ids}}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
    ]
    conn_counts = {
        doc["_id"]: doc["count"]
        async for doc in db.snowflake_connections.aggregate(conn_pipeline)
    }

    for u in users:
        u["connection_count"] = conn_counts.get(u["user_id"], 0)

    return users


@router.get("/users/{user_id}")
async def admin_user_detail(user_id: str, _: str = Depends(get_current_admin_user)):
    user = await db.users.find_one(
        {"user_id": user_id}, {"password_hash": 0, "_id": 0}
    )
    if not user:
        raise HTTPException(404, "User not found")

    connections = await db.snowflake_connections.find(
        {"user_id": user_id}, {"_id": 0, "private_key_encrypted": 0}
    ).to_list(length=100)

    alert_count = await db.alerts.count_documents({"user_id": user_id})

    # Query summary aggregation
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total_queries": {"$sum": 1},
            "total_cost_usd": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
            "latest_query_date": {"$max": "$end_time"},
        }},
    ]
    summary_cursor = db.query_history.aggregate(pipeline)
    summary_doc = await summary_cursor.to_list(length=1)
    if summary_doc:
        query_summary = {
            "total_queries": summary_doc[0]["total_queries"],
            "total_cost_usd": round(summary_doc[0].get("total_cost_usd") or 0, 2),
            "latest_query_date": summary_doc[0].get("latest_query_date"),
        }
    else:
        query_summary = {"total_queries": 0, "total_cost_usd": 0, "latest_query_date": None}

    return {
        **user,
        "connections": connections,
        "alert_count": alert_count,
        "query_summary": query_summary,
    }


@router.patch("/users/{user_id}/role")
async def admin_set_role(user_id: str, _: str = Depends(get_current_admin_user)):
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    new_role = None if user.get("role") == "admin" else "admin"
    await db.users.update_one({"user_id": user_id}, {"$set": {"role": new_role}})
    return {"user_id": user_id, "role": new_role}


@router.patch("/users/{user_id}/toggle-disable")
async def admin_toggle_disable(user_id: str, _: str = Depends(get_current_admin_user)):
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    new_status = not user.get("is_disabled", False)
    await db.users.update_one({"user_id": user_id}, {"$set": {"is_disabled": new_status}})
    return {"user_id": user_id, "is_disabled": new_status}


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, _: str = Depends(get_current_admin_user)):
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    await db.users.delete_one({"user_id": user_id})
    await db.snowflake_connections.delete_many({"user_id": user_id})
    await db.alerts.delete_many({"user_id": user_id})
    await db.query_history.delete_many({"user_id": user_id})
    return {"message": "User deleted", "user_id": user_id}


@router.get("/users/{user_id}/queries")
async def admin_user_queries(
    user_id: str,
    _: str = Depends(get_current_admin_user),
    limit: int = Query(default=10, le=100),
    skip: int = Query(default=0, ge=0),
):
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    # Summary stats
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total_queries": {"$sum": 1},
            "total_cost_usd": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
            "avg_duration_ms": {"$avg": {"$ifNull": ["$total_elapsed_time", 0]}},
        }},
    ]
    summary_cursor = db.query_history.aggregate(pipeline)
    summary_doc = await summary_cursor.to_list(length=1)
    summary = {
        "total_queries": summary_doc[0]["total_queries"] if summary_doc else 0,
        "total_cost_usd": round(summary_doc[0].get("total_cost_usd", 0), 2) if summary_doc else 0,
        "avg_duration_ms": round(summary_doc[0].get("avg_duration_ms", 0), 1) if summary_doc else 0,
    }

    # Paginated queries
    queries = await db.query_history.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("end_time", -1).skip(skip).limit(limit).to_list(length=limit)

    return {"summary": summary, "queries": queries}


@router.get("/users/{user_id}/recommendations")
async def admin_user_recommendations(user_id: str, _: str = Depends(get_current_admin_user)):
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    conn = await db.snowflake_connections.find_one({"user_id": user_id, "is_active": True})
    if not conn:
        return []

    try:
        recs = await run_in_thread(sync_recommendations, conn, 3.0)
        return recs
    except Exception:
        return []


@router.get("/activity")
async def admin_activity(_: str = Depends(get_current_admin_user)):
    # Recent signups
    recent_users = await db.users.find(
        {}, {"password_hash": 0, "_id": 0}
    ).sort("created_at", -1).limit(20).to_list(length=20)

    signups = [
        {
            "type": "signup",
            "user_name": u.get("name", "Unknown"),
            "user_email": u.get("email"),
            "auth_provider": u.get("auth_provider", "email"),
            "timestamp": u.get("created_at"),
        }
        for u in recent_users
    ]

    # Recent connections created
    recent_connections = await db.snowflake_connections.find(
        {}, {"_id": 0, "private_key_encrypted": 0}
    ).sort("created_at", -1).limit(20).to_list(length=20)

    connection_events = [
        {
            "type": "connection_created",
            "user_id": c.get("user_id"),
            "account": c.get("account"),
            "timestamp": c.get("created_at"),
        }
        for c in recent_connections
    ]

    # Merge and sort by timestamp descending
    activity = sorted(
        signups + connection_events,
        key=lambda x: x.get("timestamp") or "",
        reverse=True,
    )[:30]

    return activity
