from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_current_user, get_data_source
from app.services.agent import run_agent
from app.services.snowflake import get_credit_price

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    messages: list[dict]  # [{"role": "user", "content": "..."}, ...]


class ChatResponse(BaseModel):
    response: str
    demo: bool = False


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    if not body.messages:
        raise HTTPException(400, "Messages cannot be empty")

    source = await get_data_source(user_id)
    credit_price = 3.0
    if source:
        credit_price = await get_credit_price(source)

    response = await run_agent(body.messages, source, credit_price, user_id=user_id)
    return ChatResponse(response=response, demo=source is None)
