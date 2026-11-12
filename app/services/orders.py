"""Workflow 3 (часть 2): оформление заказа из примерочной и смена статуса."""

from datetime import datetime, timezone

from app import storage
from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.schemas.orders import OrderStatus
from app.services import users as users_service

# из какого статуса в какой можно перейти
ALLOWED_TRANSITIONS = {
    OrderStatus.pending: [OrderStatus.paid, OrderStatus.cancelled],
    OrderStatus.paid: [OrderStatus.shipped, OrderStatus.cancelled],
    OrderStatus.shipped: [],
    OrderStatus.cancelled: [],
}


def create_order(user_id: int) -> dict:
    users_service.get_user(user_id)
    room = storage.fitting_rooms[user_id]
    if not room:
        raise BusinessRuleError("Fitting room is empty")

    # повторная проверка: остаток мог измениться, пока товар лежал в примерочной
    for position in room:
        item = storage.items[position["item_id"]]
        if position["quantity"] > item["stock"]:
            raise ConflictError(f"Not enough stock for item {item['id']}: {item['stock']} left")

    # все проверки пройдены — списываем остатки и собираем снапшот заказа
    order_items = []
    total = 0
    for position in room:
        item = storage.items[position["item_id"]]
        item["stock"] -= position["quantity"]
        order_items.append(
            {
                "item_id": item["id"],
                "name": item["name"],
                "price": item["price"],
                "quantity": position["quantity"],
            }
        )
        total += item["price"] * position["quantity"]

    order = {
        "id": storage.next_id("order"),
        "user_id": user_id,
        "items": order_items,
        "total": total,
        "status": OrderStatus.pending,
        "created_at": datetime.now(timezone.utc),
    }
    storage.orders[order["id"]] = order
    room.clear()
    return order


def list_user_orders(user_id: int) -> list[dict]:
    users_service.get_user(user_id)
    return [order for order in storage.orders.values() if order["user_id"] == user_id]


def get_order(order_id: int) -> dict:
    if order_id not in storage.orders:
        raise NotFoundError(f"Order {order_id} not found")
    return storage.orders[order_id]


def change_status(order_id: int, new_status: OrderStatus) -> dict:
    order = get_order(order_id)
    if new_status not in ALLOWED_TRANSITIONS[order["status"]]:
        raise ConflictError(f"Cannot change order status from {order['status']} to {new_status}")

    # при отмене возвращаем товары на склад (если товар за это время не удалили)
    if new_status == OrderStatus.cancelled:
        for row in order["items"]:
            if row["item_id"] in storage.items:
                storage.items[row["item_id"]]["stock"] += row["quantity"]

    order["status"] = new_status
    return order
