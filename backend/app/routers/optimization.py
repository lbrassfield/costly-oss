from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException

from app.deps import get_current_user, get_data_source
from app.services.cache import cache
from app.services.snowflake import (
    get_credit_price,
    sync_warehouse_sizing,
    sync_autosuspend_analysis,
    sync_spillage,
    sync_query_patterns,
    sync_cost_attribution,
    sync_stale_tables,
    sync_execute_resize,
    sync_execute_autosuspend,
)
from app.services.demo import (
    generate_demo_warehouse_sizing,
    generate_demo_autosuspend,
    generate_demo_spillage,
    generate_demo_query_patterns,
    generate_demo_cost_attribution,
    generate_demo_stale_tables,
)
from app.models.warehouse_action import WarehouseResize, WarehouseAutoSuspend
from app.utils.constants import CACHE_TTL
from app.utils.helpers import run_in_thread

router = APIRouter(tags=["optimization"])


@router.get("/api/warehouses/sizing")
async def warehouse_sizing(
    days: int = Query(30, ge=1, le=90),
    refresh: bool = Query(False),
    user_id: str = Depends(get_current_user),
):
    source = await get_data_source(user_id)
    fetched_at = datetime.utcnow().isoformat()
    if not source:
        return {**generate_demo_warehouse_sizing(), "fetched_at": fetched_at, "demo": True}
    cache_key = f"{user_id}:warehouse_sizing:{days}"
    if refresh:
        cache.delete(cache_key)
    cached = cache.get(cache_key)
    if cached:
        return {**cached, "cached": True, "fetched_at": fetched_at}
    credit_price = await get_credit_price(source)
    result = await run_in_thread(sync_warehouse_sizing, source, days, credit_price)
    cache.set(cache_key, result, CACHE_TTL["warehouse_sizing"])
    return {**result, "fetched_at": fetched_at}


@router.get("/api/warehouses/autosuspend")
async def autosuspend_analysis(
    days: int = Query(30, ge=1, le=90),
    refresh: bool = Query(False),
    user_id: str = Depends(get_current_user),
):
    source = await get_data_source(user_id)
    fetched_at = datetime.utcnow().isoformat()
    if not source:
        return {**generate_demo_autosuspend(), "fetched_at": fetched_at, "demo": True}
    cache_key = f"{user_id}:autosuspend:{days}"
    if refresh:
        cache.delete(cache_key)
    cached = cache.get(cache_key)
    if cached:
        return {**cached, "cached": True, "fetched_at": fetched_at}
    credit_price = await get_credit_price(source)
    result = await run_in_thread(sync_autosuspend_analysis, source, days, credit_price)
    cache.set(cache_key, result, CACHE_TTL["autosuspend"])
    return {**result, "fetched_at": fetched_at}


@router.get("/api/spillage")
async def spillage(
    days: int = Query(30, ge=1, le=90),
    refresh: bool = Query(False),
    user_id: str = Depends(get_current_user),
):
    source = await get_data_source(user_id)
    fetched_at = datetime.utcnow().isoformat()
    if not source:
        return {**generate_demo_spillage(), "fetched_at": fetched_at, "demo": True}
    cache_key = f"{user_id}:spillage:{days}"
    if refresh:
        cache.delete(cache_key)
    cached = cache.get(cache_key)
    if cached:
        return {**cached, "cached": True, "fetched_at": fetched_at}
    result = await run_in_thread(sync_spillage, source, days)
    cache.set(cache_key, result, CACHE_TTL["spillage"])
    return {**result, "fetched_at": fetched_at}


@router.get("/api/query-patterns")
async def query_patterns(
    days: int = Query(30, ge=1, le=90),
    refresh: bool = Query(False),
    user_id: str = Depends(get_current_user),
):
    source = await get_data_source(user_id)
    fetched_at = datetime.utcnow().isoformat()
    if not source:
        return {**generate_demo_query_patterns(), "fetched_at": fetched_at, "demo": True}
    cache_key = f"{user_id}:query_patterns:{days}"
    if refresh:
        cache.delete(cache_key)
    cached = cache.get(cache_key)
    if cached:
        return {**cached, "cached": True, "fetched_at": fetched_at}
    credit_price = await get_credit_price(source)
    result = await run_in_thread(sync_query_patterns, source, days, credit_price)
    cache.set(cache_key, result, CACHE_TTL["query_patterns"])
    return {**result, "fetched_at": fetched_at}


@router.get("/api/cost-attribution")
async def cost_attribution(
    days: int = Query(30, ge=1, le=90),
    refresh: bool = Query(False),
    user_id: str = Depends(get_current_user),
):
    source = await get_data_source(user_id)
    fetched_at = datetime.utcnow().isoformat()
    if not source:
        return {**generate_demo_cost_attribution(), "fetched_at": fetched_at, "demo": True}
    cache_key = f"{user_id}:cost_attribution:{days}"
    if refresh:
        cache.delete(cache_key)
    cached = cache.get(cache_key)
    if cached:
        return {**cached, "cached": True, "fetched_at": fetched_at}
    credit_price = await get_credit_price(source)
    result = await run_in_thread(sync_cost_attribution, source, days, credit_price)
    cache.set(cache_key, result, CACHE_TTL["cost_attribution"])
    return {**result, "fetched_at": fetched_at}


@router.get("/api/stale-tables")
async def stale_tables(
    days: int = Query(30, ge=1, le=90),
    refresh: bool = Query(False),
    user_id: str = Depends(get_current_user),
):
    source = await get_data_source(user_id)
    fetched_at = datetime.utcnow().isoformat()
    if not source:
        return {**generate_demo_stale_tables(), "fetched_at": fetched_at, "demo": True}
    cache_key = f"{user_id}:stale_tables:{days}"
    if refresh:
        cache.delete(cache_key)
    cached = cache.get(cache_key)
    if cached:
        return {**cached, "cached": True, "fetched_at": fetched_at}
    result = await run_in_thread(sync_stale_tables, source, days)
    cache.set(cache_key, result, CACHE_TTL["stale_tables"])
    return {**result, "fetched_at": fetched_at}


@router.post("/api/warehouses/{name}/resize")
async def resize_warehouse(
    name: str,
    body: WarehouseResize,
    user_id: str = Depends(get_current_user),
):
    source = await get_data_source(user_id)
    if not source:
        raise HTTPException(400, "Cannot execute DDL in demo mode. Connect a Snowflake account first.")
    result = await run_in_thread(sync_execute_resize, source, name, body.new_size)
    if result.get("success"):
        cache.delete_prefix(f"{user_id}:warehouse")
    return result


@router.post("/api/warehouses/{name}/autosuspend")
async def update_autosuspend(
    name: str,
    body: WarehouseAutoSuspend,
    user_id: str = Depends(get_current_user),
):
    source = await get_data_source(user_id)
    if not source:
        raise HTTPException(400, "Cannot execute DDL in demo mode. Connect a Snowflake account first.")
    result = await run_in_thread(sync_execute_autosuspend, source, name, body.seconds)
    if result.get("success"):
        cache.delete_prefix(f"{user_id}:autosuspend")
        cache.delete_prefix(f"{user_id}:warehouse")
    return result
