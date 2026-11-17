from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.orders import OrderOut, OrderStatusUpdate
from app.services import orders as orders_service

router = APIRouter(tags=["3. Примерочная и заказы"])


@router.post("/users/{user_id}/orders", response_model=OrderOut, status_code=201)
def create_order(user_id: int, db: Session = Depends(get_db)):
    return orders_service.create_order(db, user_id)


@router.get("/users/{user_id}/orders", response_model=list[OrderOut])
def list_user_orders(user_id: int, db: Session = Depends(get_db)):
    return orders_service.list_user_orders(db, user_id)


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return orders_service.get_order(db, order_id)


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def change_status(order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_db)):
    return orders_service.change_status(db, order_id, data.status)
