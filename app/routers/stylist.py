from fastapi import APIRouter

from app.schemas.stylist import StylistRequest, StylistResponse
from app.services import stylist as stylist_service

router = APIRouter(tags=["4. AI-стилист"])


@router.post("/users/{user_id}/stylist", response_model=StylistResponse)
async def ask_stylist(user_id: int, data: StylistRequest):
    return await stylist_service.suggest_outfit(user_id, data)
