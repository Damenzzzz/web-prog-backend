from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import BusinessRuleError, NotFoundError
from app.models import FittingRoomRow
from app.schemas.fitting_room import FittingRoomAdd
from app.services import items as items_service
from app.services import users as users_service

MAX_POSITIONS = 10


def find_row(db: Session, user_id: int, item_id: int) -> FittingRoomRow | None:
    return db.scalar(select(FittingRoomRow).where(FittingRoomRow.user_id == user_id, FittingRoomRow.item_id == item_id))


def get_room(db: Session, user_id: int) -> dict:
    user = users_service.get_user(db, user_id)
    rows = []
    total = 0
    for row in user.fitting_room:
        subtotal = row.item.price * row.quantity
        rows.append({"item": row.item, "quantity": row.quantity, "subtotal": subtotal})
        total += subtotal
    return {"user_id": user_id, "items": rows, "total": total}


def add_item(db: Session, user_id: int, data: FittingRoomAdd) -> dict:
    user = users_service.get_user(db, user_id)
    item = items_service.get_item(db, data.item_id)
    row = find_row(db, user_id, data.item_id)
    new_quantity = data.quantity + (row.quantity if row else 0)
    if row is None and len(user.fitting_room) >= MAX_POSITIONS:
        raise BusinessRuleError(f"Fitting room is full: maximum {MAX_POSITIONS} positions")
    if new_quantity > item.stock:
        raise BusinessRuleError(f"Only {item.stock} of item {item.id} in stock")
    if row is None:
        db.add(FittingRoomRow(user_id=user_id, item_id=item.id, quantity=new_quantity))
    else:
        row.quantity = new_quantity
    db.commit()
    db.refresh(user)
    return get_room(db, user_id)


def update_quantity(db: Session, user_id: int, item_id: int, quantity: int) -> dict:
    users_service.get_user(db, user_id)
    row = find_row(db, user_id, item_id)
    if row is None:
        raise NotFoundError(f"Item {item_id} is not in the fitting room")
    if quantity > row.item.stock:
        raise BusinessRuleError(f"Only {row.item.stock} of item {item_id} in stock")
    row.quantity = quantity
    db.commit()
    return get_room(db, user_id)


def remove_item(db: Session, user_id: int, item_id: int) -> None:
    users_service.get_user(db, user_id)
    row = find_row(db, user_id, item_id)
    if row is None:
        raise NotFoundError(f"Item {item_id} is not in the fitting room")
    db.delete(row)
    db.commit()
