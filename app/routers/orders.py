from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import ensure_owner_or_admin, get_current_user
from app.exceptions import ForbiddenError
from app.models import User
from app.schemas.orders import OrderOut, OrderStatus, OrderStatusUpdate
from app.schemas.users import Role
from app.services import orders as orders_service

router = APIRouter(tags=["3. Примерочная и заказы"])

# Какие статусы владелец может поставить своему заказу сам. «Отправлен» ставит только админ (магазин).
OWNER_STATUSES = [OrderStatus.paid, OrderStatus.cancelled]


@router.post("/users/{user_id}/orders", response_model=OrderOut, status_code=201)
def create_order(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    return orders_service.create_order(db, user_id)


@router.get("/users/{user_id}/orders", response_model=list[OrderOut])
def list_user_orders(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    return orders_service.list_user_orders(db, user_id)


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = orders_service.get_order(db, order_id)
    ensure_owner_or_admin(order.user_id, current_user)
    return order


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def change_status(order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = orders_service.get_order(db, order_id)
    ensure_owner_or_admin(order.user_id, current_user)
    if current_user.role != Role.admin and data.status not in OWNER_STATUSES:
        raise ForbiddenError(f"Only admin can set status {data.status}")
    return orders_service.change_status(db, order_id, data.status)
