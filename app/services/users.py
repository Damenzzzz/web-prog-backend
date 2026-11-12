"""Workflow 2: профиль (анкета) пользователя."""

from app import storage
from app.exceptions import BusinessRuleError, ConflictError, NotFoundError, UnsupportedMediaError
from app.schemas.orders import OrderStatus
from app.schemas.users import UserCreate, UserUpdate

# заказы в этих статусах ещё «в работе»
ACTIVE_STATUSES = [OrderStatus.pending, OrderStatus.paid]

MAX_PHOTO_BYTES = 5 * 1024 * 1024


def list_users() -> list[dict]:
    return list(storage.users.values())


def get_user(user_id: int) -> dict:
    if user_id not in storage.users:
        raise NotFoundError(f"User {user_id} not found")
    return storage.users[user_id]


def create_user(data: UserCreate) -> dict:
    user = data.model_dump()
    user["id"] = storage.next_id("user")
    user["photo_url"] = None
    storage.users[user["id"]] = user
    storage.fitting_rooms[user["id"]] = []  # у каждого пользователя одна примерочная
    return user


def update_user(user_id: int, data: UserUpdate) -> dict:
    user = get_user(user_id)
    user.update(data.model_dump(exclude_none=True))  # только переданные поля
    return user


def save_photo(user_id: int, data: bytes) -> dict:
    user = get_user(user_id)
    # принимаем только JPEG и PNG; формат определяем по первым байтам файла, а не по имени
    if data.startswith(b"\xff\xd8\xff"):
        extension = "jpg"
    elif data.startswith(b"\x89PNG"):
        extension = "png"
    else:
        raise UnsupportedMediaError("Only JPEG and PNG photos are allowed")
    if len(data) > MAX_PHOTO_BYTES:
        raise BusinessRuleError("Photo is larger than 5 MB")

    storage.delete_file(user["photo_url"])
    user["photo_url"] = f"/uploads/user_{user_id}.{extension}"
    storage.static_path(user["photo_url"]).write_bytes(data)
    return user


def delete_user(user_id: int) -> None:
    user = get_user(user_id)
    # нельзя удалить пользователя, пока у него есть неоплаченный или неотправленный заказ
    for order in storage.orders.values():
        if order["user_id"] == user_id and order["status"] in ACTIVE_STATUSES:
            raise ConflictError(f"User {user_id} has active order {order['id']} ({order['status']})")

    # вместе с пользователем удаляем его фото и все примерки с файлами
    storage.delete_file(user["photo_url"])
    for try_on in list(storage.try_ons.values()):
        if try_on["user_id"] == user_id:
            storage.delete_file(try_on["result_url"])
            del storage.try_ons[try_on["id"]]
    storage.try_on_times.pop(user_id, None)

    del storage.users[user_id]
    del storage.fitting_rooms[user_id]
