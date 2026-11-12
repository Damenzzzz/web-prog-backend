from fastapi import APIRouter

from app.schemas.orders import OrderOut, OrderStatusUpdate
from app.services import orders as orders_service

router = APIRouter(tags=["3. Примерочная и заказы"])


@router.post("/users/{user_id}/orders", response_model=OrderOut, status_code=201)
async def create_order(user_id: int):
    return orders_service.create_order(user_id)


@router.get("/users/{user_id}/orders", response_model=list[OrderOut])
async def list_user_orders(user_id: int):
    return orders_service.list_user_orders(user_id)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(order_id: int):
    return orders_service.get_order(order_id)


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
async def change_status(order_id: int, data: OrderStatusUpdate):
    return orders_service.change_status(order_id, data.status)
