from fastapi import APIRouter

from app.schemas.try_on import TryOnCreate, TryOnOut
from app.services import try_on as try_on_service

router = APIRouter(tags=["4. AI-примерка"])


@router.post("/users/{user_id}/try-ons", response_model=TryOnOut, status_code=201)
async def create_try_on(user_id: int, data: TryOnCreate):
    return await try_on_service.create_try_on(user_id, data)


@router.get("/users/{user_id}/try-ons", response_model=list[TryOnOut])
async def list_user_try_ons(user_id: int):
    return try_on_service.list_user_try_ons(user_id)


@router.get("/try-ons/{try_on_id}", response_model=TryOnOut)
async def get_try_on(try_on_id: int):
    return try_on_service.get_try_on(try_on_id)


@router.delete("/try-ons/{try_on_id}", status_code=204)
async def delete_try_on(try_on_id: int) -> None:
    try_on_service.delete_try_on(try_on_id)
