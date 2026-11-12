from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class OrderStatus(StrEnum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    cancelled = "cancelled"


class OrderItem(BaseModel):
    # снапшот товара на момент заказа: цена в заказе не меняется, даже если товар потом изменят
    item_id: int
    name: str
    price: int
    quantity: int


class OrderOut(BaseModel):
    id: int
    user_id: int
    items: list[OrderItem]
    total: int
    status: OrderStatus
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
