from fastapi import APIRouter

from app.schemas.fitting_room import FittingRoomAdd, FittingRoomOut, QuantityUpdate
from app.services import fitting_room as fitting_room_service

router = APIRouter(prefix="/users/{user_id}/fitting-room", tags=["3. Примерочная и заказы"])


@router.get("", response_model=FittingRoomOut)
async def get_room(user_id: int):
    return fitting_room_service.get_room(user_id)


@router.post("/items", response_model=FittingRoomOut, status_code=201)
async def add_item(user_id: int, data: FittingRoomAdd):
    return fitting_room_service.add_item(user_id, data)


@router.patch("/items/{item_id}", response_model=FittingRoomOut)
async def update_quantity(user_id: int, item_id: int, data: QuantityUpdate):
    return fitting_room_service.update_quantity(user_id, item_id, data.quantity)


@router.delete("/items/{item_id}", status_code=204)
async def remove_item(user_id: int, item_id: int) -> None:
    fitting_room_service.remove_item(user_id, item_id)
