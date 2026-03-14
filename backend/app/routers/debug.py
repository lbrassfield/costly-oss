from fastapi import APIRouter, HTTPException, Depends

from app.deps import get_current_user, get_data_source
from app.services.snowflake import sync_debug_permissions
from app.utils.helpers import run_in_thread

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/permissions")
async def debug_permissions(user_id: str = Depends(get_current_user)):
    source = await get_data_source(user_id)
    if not source:
        raise HTTPException(400, "No active Snowflake connection.")
    results = await run_in_thread(sync_debug_permissions, source)
    return {"connection": source.get("account"), "role": source.get("role"), "checks": results}
