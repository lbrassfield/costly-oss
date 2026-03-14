from pydantic import BaseModel
from typing import Optional


class AlertCreate(BaseModel):
    name: str
    metric: str
    threshold: float
    channel: str
    webhook_url: Optional[str] = None


class AlertUpdate(BaseModel):
    enabled: Optional[bool] = None
