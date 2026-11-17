from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import FittingRoomRow, Item, Look
from app.schemas.items import Category, ItemCreate, ItemUpdate

NEUTRAL_COLORS = {"белый", "чёрный", "серый", "бежевый"}

MATCHING_CATEGORIES = {
    Category.top: [Category.bottom, Category.shoes, Category.bag, Category.outerwear],
    Category.bottom: [Category.top, Category.shoes, Category.outerwear],
    Category.outerwear: [Category.top, Category.bottom, Category.shoes],
    Category.shoes: [Category.top, Category.bottom, Category.bag],
    Category.bag: [Category.top, Category.shoes, Category.accessory],
    Category.accessory: [Category.top, Category.bag, Category.outerwear],
}


def list_items(db: Session, category=None, color=None, min_price=None, max_price=None, in_stock=None) -> list[Item]:
    query = select(Item).order_by(Item.id)
    if category is not None:
        query = query.where(Item.category == category)
    if color is not None:
        query = query.where(func.lower(Item.color) == color.lower())
    if min_price is not None:
        query = query.where(Item.price >= min_price)
    if max_price is not None:
        query = query.where(Item.price <= max_price)
    if in_stock is True:
        query = query.where(Item.stock > 0)
    if in_stock is False:
        query = query.where(Item.stock == 0)
    return list(db.scalars(query))


def get_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise NotFoundError(f"Item {item_id} not found")
    return item


def create_item(db: Session, data: ItemCreate) -> Item:
    if data.look_id is not None:
        get_look(db, data.look_id)
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    return item


def update_item(db: Session, item_id: int, data: ItemUpdate) -> Item:
    item = get_item(db, item_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("name", "category", "color", "price", "stock"):
        if field in changes and changes[field] is None:
            raise BusinessRuleError(f"Field {field} cannot be null")
    if changes.get("look_id") is not None:
        get_look(db, changes["look_id"])
    for field, value in changes.items():
        setattr(item, field, value)
    db.commit()
    return item


def delete_item(db: Session, item_id: int) -> None:
    item = get_item(db, item_id)
    row = db.scalar(select(FittingRoomRow).where(FittingRoomRow.item_id == item_id))
    if row is not None:
        raise ConflictError(f"Item {item_id} is in the fitting room of user {row.user_id}")
    db.delete(item)
    db.commit()


def get_look(db: Session, look_id: int) -> Look:
    look = db.get(Look, look_id)
    if look is None:
        raise NotFoundError(f"Look {look_id} not found")
    return look


def list_looks(db: Session) -> list[Look]:
    return list(db.scalars(select(Look).order_by(Look.id)))


def colors_match(first: str, second: str) -> bool:
    first, second = first.lower(), second.lower()
    return first == second or first in NEUTRAL_COLORS or second in NEUTRAL_COLORS


def find_matches(db: Session, item_id: int, limit: int = 4) -> list[Item]:
    item = get_item(db, item_id)
    query = select(Item).where(
        Item.id != item_id,
        Item.stock > 0,
        Item.category.in_(MATCHING_CATEGORIES[item.category]),
    ).order_by(Item.id)
    candidates = [other for other in db.scalars(query) if colors_match(item.color, other.color)]
    candidates.sort(key=lambda other: other.look_id != item.look_id)
    result = []
    used_categories = set()
    for other in candidates:
        if other.category not in used_categories:
            result.append(other)
            used_categories.add(other.category)
    result += [other for other in candidates if other not in result]
    return result[:limit]
