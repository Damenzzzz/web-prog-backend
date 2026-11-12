from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    top = "top"
    bottom = "bottom"
    outerwear = "outerwear"
    shoes = "shoes"
    bag = "bag"
    accessory = "accessory"


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: Category
    color: str = Field(min_length=1, max_length=30)
    price: int = Field(gt=0)
    stock: int = Field(ge=0)
    look_id: int | None = None
    image_url: str | None = None


class ItemUpdate(BaseModel):
    # PATCH: все поля необязательные, меняются только переданные
    name: str | None = Field(None, min_length=1, max_length=100)
    category: Category | None = None
    color: str | None = Field(None, min_length=1, max_length=30)
    price: int | None = Field(None, gt=0)
    stock: int | None = Field(None, ge=0)
    look_id: int | None = None
    image_url: str | None = None


class ItemOut(ItemCreate):
    id: int


class LookOut(BaseModel):
    id: int
    title: str
    item_ids: list[int]


class LookDetail(LookOut):
    items: list[ItemOut]
