from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import ensure_owner_or_admin, get_current_user
from app.models import User
from app.schemas.fitting_room import FittingRoomAdd, FittingRoomOut, QuantityUpdate
from app.services import fitting_room as fitting_room_service

router = APIRouter(prefix="/users/{user_id}/fitting-room", tags=["3. Примерочная и заказы"])


@router.get("", response_model=FittingRoomOut)
def get_room(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    return fitting_room_service.get_room(db, user_id)


@router.post("/items", response_model=FittingRoomOut, status_code=201)
def add_item(user_id: int, data: FittingRoomAdd, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    return fitting_room_service.add_item(db, user_id, data)


@router.patch("/items/{item_id}", response_model=FittingRoomOut)
def update_quantity(user_id: int, item_id: int, data: QuantityUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    return fitting_room_service.update_quantity(db, user_id, item_id, data.quantity)


@router.delete("/items/{item_id}", status_code=204)
def remove_item(user_id: int, item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    ensure_owner_or_admin(user_id, current_user)
    fitting_room_service.remove_item(db, user_id, item_id)
