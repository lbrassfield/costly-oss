from pydantic import BaseModel, Field

class WarehouseResize(BaseModel):
    new_size: str

class WarehouseAutoSuspend(BaseModel):
    seconds: int = Field(..., ge=0, le=86400)
