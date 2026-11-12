"""Workflow 1: каталог, образы и рекомендации «дополни образ»."""

from app import storage
from app.exceptions import ConflictError, NotFoundError
from app.schemas.items import Category, ItemCreate, ItemUpdate

# нейтральные цвета подходят к любому цвету
NEUTRAL_COLORS = {"белый", "чёрный", "серый", "бежевый"}

# какие категории сочетаются с данной
MATCHING_CATEGORIES = {
    Category.top: [Category.bottom, Category.shoes, Category.bag, Category.outerwear],
    Category.bottom: [Category.top, Category.shoes, Category.outerwear],
    Category.outerwear: [Category.top, Category.bottom, Category.shoes],
    Category.shoes: [Category.top, Category.bottom, Category.bag],
    Category.bag: [Category.top, Category.shoes, Category.accessory],
    Category.accessory: [Category.top, Category.bag, Category.outerwear],
}


def list_items(category=None, color=None, min_price=None, max_price=None, in_stock=None) -> list[dict]:
    result = list(storage.items.values())
    if category is not None:
        result = [item for item in result if item["category"] == category]
    if color is not None:
        result = [item for item in result if item["color"].lower() == color.lower()]
    if min_price is not None:
        result = [item for item in result if item["price"] >= min_price]
    if max_price is not None:
        result = [item for item in result if item["price"] <= max_price]
    if in_stock is not None:
        result = [item for item in result if (item["stock"] > 0) == in_stock]
    return result


def get_item(item_id: int) -> dict:
    if item_id not in storage.items:
        raise NotFoundError(f"Item {item_id} not found")
    return storage.items[item_id]


def create_item(data: ItemCreate) -> dict:
    if data.look_id is not None:
        get_look(data.look_id)  # образ должен существовать
    item = data.model_dump()
    item["id"] = storage.next_id("item")
    storage.items[item["id"]] = item
    return item


def update_item(item_id: int, data: ItemUpdate) -> dict:
    item = get_item(item_id)
    changes = data.model_dump(exclude_none=True)  # только переданные поля
    if "look_id" in changes:
        get_look(changes["look_id"])
    item.update(changes)
    return item


def delete_item(item_id: int) -> None:
    get_item(item_id)
    # нельзя удалить товар, который лежит в чьей-то примерочной
    for user_id, room in storage.fitting_rooms.items():
        for position in room:
            if position["item_id"] == item_id:
                raise ConflictError(f"Item {item_id} is in the fitting room of user {user_id}")
    del storage.items[item_id]


def get_look(look_id: int) -> dict:
    if look_id not in storage.looks:
        raise NotFoundError(f"Look {look_id} not found")
    look = storage.looks[look_id]
    # состав образа считаем по полю look_id у товаров, чтобы не хранить связь в двух местах
    look_items = [item for item in storage.items.values() if item["look_id"] == look_id]
    return {
        "id": look["id"],
        "title": look["title"],
        "item_ids": [item["id"] for item in look_items],
        "items": look_items,
    }


def list_looks() -> list[dict]:
    return [get_look(look_id) for look_id in storage.looks]


def colors_match(first: str, second: str) -> bool:
    first, second = first.lower(), second.lower()
    return first == second or first in NEUTRAL_COLORS or second in NEUTRAL_COLORS


def find_matches(item_id: int, limit: int = 4) -> list[dict]:
    """Рекомендации без ML: подходящая категория + сочетающийся цвет + есть в наличии."""
    item = get_item(item_id)
    candidates = [
        other
        for other in storage.items.values()
        if other["id"] != item_id
        and other["stock"] > 0
        and other["category"] in MATCHING_CATEGORIES[item["category"]]
        and colors_match(item["color"], other["color"])
    ]
    # вещи из того же образа ставим первыми (сортировка устойчивая, порядок по id сохраняется)
    candidates.sort(key=lambda other: other["look_id"] != item["look_id"])

    # сначала берём по одной вещи из каждой категории, потом добираем остальными
    result = []
    used_categories = set()
    for other in candidates:
        if other["category"] not in used_categories:
            result.append(other)
            used_categories.add(other["category"])
    result += [other for other in candidates if other not in result]
    return result[:limit]
