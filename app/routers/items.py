from fastapi import APIRouter, Query

from app.schemas.items import Category, ItemCreate, ItemOut, ItemUpdate, LookDetail, LookOut
from app.services import items as items_service

router = APIRouter(tags=["1. Каталог и образы"])


@router.get("/items", response_model=list[ItemOut])
async def list_items(
    category: Category | None = None,
    color: str | None = None,
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    in_stock: bool | None = None,
):
    return items_service.list_items(category, color, min_price, max_price, in_stock)


@router.get("/items/{item_id}", response_model=ItemOut)
async def get_item(item_id: int):
    return items_service.get_item(item_id)


@router.post("/items", response_model=ItemOut, status_code=201)
async def create_item(data: ItemCreate):
    return items_service.create_item(data)


@router.patch("/items/{item_id}", response_model=ItemOut)
async def update_item(item_id: int, data: ItemUpdate):
    return items_service.update_item(item_id, data)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int) -> None:
    items_service.delete_item(item_id)


@router.get("/items/{item_id}/matches", response_model=list[ItemOut])
async def get_matches(item_id: int, limit: int = Query(4, ge=1, le=20)):
    return items_service.find_matches(item_id, limit)


@router.get("/looks", response_model=list[LookOut])
async def list_looks():
    return items_service.list_looks()


@router.get("/looks/{look_id}", response_model=LookDetail)
async def get_look(look_id: int):
    return items_service.get_look(look_id)
