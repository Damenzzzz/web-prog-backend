from pydantic import BaseModel, Field

from app.schemas.items import ItemOut


class FittingRoomAdd(BaseModel):
    item_id: int
    quantity: int = Field(1, ge=1)


class QuantityUpdate(BaseModel):
    quantity: int = Field(ge=1)


class FittingRoomRow(BaseModel):
    item: ItemOut
    quantity: int
    subtotal: int


class FittingRoomOut(BaseModel):
    user_id: int
    items: list[FittingRoomRow]
    total: int
