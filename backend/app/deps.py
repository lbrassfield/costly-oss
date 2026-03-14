from fastapi import Depends, HTTPException, Header
from jose import JWTError, jwt

from app.config import settings
from app.database import db


async def get_current_user(authorization: str = Header(...)):
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Invalid auth header format")
        token = authorization[7:]
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") == "refresh":
            raise HTTPException(401, "Cannot use refresh token for API access")
        return payload["user_id"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Authentication failed")


async def get_current_admin_user(user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"user_id": user_id})
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return user_id


async def get_data_source(user_id: str):
    return await db.snowflake_connections.find_one({"user_id": user_id, "is_active": True})
