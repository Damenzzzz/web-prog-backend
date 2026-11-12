"""Workflow 4: AI-примерка — Gemini «надевает» выбранные вещи на фото пользователя."""

import base64
import mimetypes
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import llm, storage
from app.exceptions import BusinessRuleError, LLMError, NotFoundError, TooManyRequestsError
from app.schemas.try_on import TryOnCreate, TryOnStatus
from app.services import items as items_service
from app.services import users as users_service

DAILY_LIMIT = 3


async def create_try_on(user_id: int, data: TryOnCreate) -> dict:
    user = users_service.get_user(user_id)
    if user["photo_url"] is None:
        raise BusinessRuleError("Upload your photo before trying clothes on")
    items = [items_service.get_item(item_id) for item_id in data.item_ids]

    # в одной примерке не больше одной вещи каждой категории
    categories = [item["category"] for item in items]
    if len(set(categories)) < len(categories):
        raise BusinessRuleError("Only one item per category can be tried on")

    photos = [storage.static_path(user["photo_url"])] + [item_photo(item) for item in items]

    # не больше 3 примерок на пользователя за последние 24 часа (неудачные попытки тоже считаются)
    now = datetime.now(timezone.utc)
    recent = [time for time in storage.try_on_times.get(user_id, []) if now - time < timedelta(days=1)]
    if len(recent) >= DAILY_LIMIT:
        raise TooManyRequestsError(f"Daily limit reached: {DAILY_LIMIT} try-ons per day")
    storage.try_on_times[user_id] = recent + [now]

    mock = os.getenv("LLM_MOCK", "").lower() == "true"
    try_on = {
        "id": storage.next_id("try_on"),
        "user_id": user_id,
        "item_ids": data.item_ids,
        "status": TryOnStatus.failed,
        "source": "mock" if mock else "gemini",
        "result_url": None,
        "error": None,
        "created_at": now,
    }
    storage.try_ons[try_on["id"]] = try_on

    if mock:
        # режим без Gemini: результат — копия фото пользователя
        result_url = f"/results/{try_on['id']}{photos[0].suffix}"
        shutil.copy(photos[0], storage.static_path(result_url))
    else:
        try:
            image = await llm.generate_try_on(build_prompt(user, items), [encode_image(photo) for photo in photos])
        except LLMError as error:
            # примерка остаётся в истории со статусом failed, клиент получает 502
            try_on["error"] = error.detail
            raise
        result_url = f"/results/{try_on['id']}.png"
        storage.static_path(result_url).write_bytes(image)

    try_on["status"] = TryOnStatus.done
    try_on["result_url"] = result_url
    return try_on


def item_photo(item: dict) -> Path:
    # Gemini нужна настоящая фотография вещи, и лежать она должна внутри static/
    path = storage.static_path(item["image_url"] or "").resolve()
    if not path.is_file() or storage.STATIC_DIR not in path.parents:
        raise BusinessRuleError(f"Item {item['id']} has no photo for try-on")
    return path


def encode_image(path: Path) -> dict:
    return {
        "mime_type": mimetypes.guess_type(path.name)[0],
        "data": base64.b64encode(path.read_bytes()).decode(),
    }


def build_prompt(user: dict, items: list[dict]) -> str:
    clothes = ", ".join(f"{item['name']} ({item['color']})" for item in items)
    return (
        "Одень человека с первого фото в вещи с остальных фото. Сохрани лицо, позу и фон.\n"
        f"Параметры человека: рост {user['height_cm']} см, вес {user['weight_kg']} кг, "
        f"тип фигуры {user['body_type']}.\n"
        f"Вещи в порядке следования фото: {clothes}.\n"
        "Верни одно фотореалистичное изображение."
    )


def list_user_try_ons(user_id: int) -> list[dict]:
    users_service.get_user(user_id)
    return [try_on for try_on in storage.try_ons.values() if try_on["user_id"] == user_id]


def get_try_on(try_on_id: int) -> dict:
    if try_on_id not in storage.try_ons:
        raise NotFoundError(f"Try-on {try_on_id} not found")
    return storage.try_ons[try_on_id]


def delete_try_on(try_on_id: int) -> None:
    try_on = get_try_on(try_on_id)
    storage.delete_file(try_on["result_url"])
    del storage.try_ons[try_on_id]
