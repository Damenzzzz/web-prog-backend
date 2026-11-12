"""Workflow 2: профиль (анкета) пользователя."""

from app import storage
from app.exceptions import ConflictError, NotFoundError
from app.schemas.orders import OrderStatus
from app.schemas.users import UserCreate, UserUpdate

# заказы в этих статусах ещё «в работе»
ACTIVE_STATUSES = [OrderStatus.pending, OrderStatus.paid]


def list_users() -> list[dict]:
    return list(storage.users.values())


def get_user(user_id: int) -> dict:
    if user_id not in storage.users:
        raise NotFoundError(f"User {user_id} not found")
    return storage.users[user_id]


def create_user(data: UserCreate) -> dict:
    user = data.model_dump()
    user["id"] = storage.next_id("user")
    storage.users[user["id"]] = user
    storage.fitting_rooms[user["id"]] = []  # у каждого пользователя одна примерочная
    return user


def update_user(user_id: int, data: UserUpdate) -> dict:
    user = get_user(user_id)
    user.update(data.model_dump(exclude_none=True))  # только переданные поля
    return user


def delete_user(user_id: int) -> None:
    get_user(user_id)
    # нельзя удалить пользователя, пока у него есть неоплаченный или неотправленный заказ
    for order in storage.orders.values():
        if order["user_id"] == user_id and order["status"] in ACTIVE_STATUSES:
            raise ConflictError(f"User {user_id} has active order {order['id']} ({order['status']})")
    del storage.users[user_id]
    del storage.fitting_rooms[user_id]
