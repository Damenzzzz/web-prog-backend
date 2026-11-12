"""Workflow 3 (часть 1): примерочная — корзина пользователя."""

from app import storage
from app.exceptions import BusinessRuleError, NotFoundError
from app.schemas.fitting_room import FittingRoomAdd
from app.services import items as items_service
from app.services import users as users_service

MAX_POSITIONS = 10


def find_position(room: list[dict], item_id: int) -> dict | None:
    for position in room:
        if position["item_id"] == item_id:
            return position
    return None


def get_room(user_id: int) -> dict:
    users_service.get_user(user_id)
    rows = []
    total = 0
    for position in storage.fitting_rooms[user_id]:
        item = storage.items[position["item_id"]]
        subtotal = item["price"] * position["quantity"]
        rows.append({"item": item, "quantity": position["quantity"], "subtotal": subtotal})
        total += subtotal
    return {"user_id": user_id, "items": rows, "total": total}


def add_item(user_id: int, data: FittingRoomAdd) -> dict:
    users_service.get_user(user_id)
    item = items_service.get_item(data.item_id)
    room = storage.fitting_rooms[user_id]
    position = find_position(room, data.item_id)

    # повторное добавление того же товара увеличивает количество, а не создаёт дубль
    new_quantity = data.quantity + (position["quantity"] if position else 0)

    if position is None and len(room) >= MAX_POSITIONS:
        raise BusinessRuleError(f"Fitting room is full: maximum {MAX_POSITIONS} positions")
    if new_quantity > item["stock"]:
        raise BusinessRuleError(f"Only {item['stock']} of item {item['id']} in stock")

    if position is None:
        room.append({"item_id": data.item_id, "quantity": new_quantity})
    else:
        position["quantity"] = new_quantity
    return get_room(user_id)


def update_quantity(user_id: int, item_id: int, quantity: int) -> dict:
    users_service.get_user(user_id)
    position = find_position(storage.fitting_rooms[user_id], item_id)
    if position is None:
        raise NotFoundError(f"Item {item_id} is not in the fitting room")
    stock = storage.items[item_id]["stock"]
    if quantity > stock:
        raise BusinessRuleError(f"Only {stock} of item {item_id} in stock")
    position["quantity"] = quantity
    return get_room(user_id)


def remove_item(user_id: int, item_id: int) -> None:
    users_service.get_user(user_id)
    room = storage.fitting_rooms[user_id]
    position = find_position(room, item_id)
    if position is None:
        raise NotFoundError(f"Item {item_id} is not in the fitting room")
    room.remove(position)
