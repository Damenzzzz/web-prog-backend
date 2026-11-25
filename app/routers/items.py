from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models import User
from app.schemas.items import Category, ItemCreate, ItemOut, ItemUpdate, LookDetail, LookOut
from app.services import items as items_service

router = APIRouter(tags=["1. Каталог и образы"])


@router.get("/items", response_model=list[ItemOut])
def list_items(
    category: Category | None = None,
    color: str | None = None,
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    in_stock: bool | None = None,
    db: Session = Depends(get_db),
):
    return items_service.list_items(db, category, color, min_price, max_price, in_stock)


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    return items_service.get_item(db, item_id)


@router.post("/items", response_model=ItemOut, status_code=201)
def create_item(data: ItemCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return items_service.create_item(db, data)


@router.patch("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return items_service.update_item(db, item_id, data)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> None:
    items_service.delete_item(db, item_id)


@router.get("/items/{item_id}/matches", response_model=list[ItemOut])
def get_matches(item_id: int, limit: int = Query(4, ge=1, le=20), db: Session = Depends(get_db)):
    return items_service.find_matches(db, item_id, limit)


@router.get("/looks", response_model=list[LookOut])
def list_looks(db: Session = Depends(get_db)):
    return items_service.list_looks(db)


@router.get("/looks/{look_id}", response_model=LookDetail)
def get_look(look_id: int, db: Session = Depends(get_db)):
    return items_service.get_look(db, look_id)
