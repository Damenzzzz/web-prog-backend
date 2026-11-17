from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class OrderStatus(StrEnum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    cancelled = "cancelled"


class OrderItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    item_id: int | None
    name: str
    price: int
    quantity: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    items: list[OrderItem]
    total: int
    status: OrderStatus
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
