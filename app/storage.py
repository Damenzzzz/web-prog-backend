"""Хранилище в памяти: обычные словари. После перезапуска сервера данные сбрасываются."""

items: dict[int, dict] = {}  # id товара -> товар
looks: dict[int, dict] = {}  # id образа -> {"id", "title"}
users: dict[int, dict] = {}  # id пользователя -> анкета
fitting_rooms: dict[int, list[dict]] = {}  # id пользователя -> [{"item_id": 1, "quantity": 2}, ...]
orders: dict[int, dict] = {}  # id заказа -> заказ

# последние выданные id для каждой сущности
_last_ids = {"item": 0, "look": 0, "user": 0, "order": 0}


def next_id(kind: str) -> int:
    _last_ids[kind] += 1
    return _last_ids[kind]
