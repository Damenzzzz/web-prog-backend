import base64
import mimetypes
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import llm, storage
from app.exceptions import BusinessRuleError, LLMError, NotFoundError, TooManyRequestsError
from app.models import Item, TryOn, User
from app.schemas.try_on import TryOnCreate, TryOnStatus
from app.services import items as items_service
from app.services import users as users_service

DAILY_LIMIT = 3


async def create_try_on(db: Session, user_id: int, data: TryOnCreate) -> TryOn:
    user = users_service.get_user(db, user_id)
    if user.photo_url is None:
        raise BusinessRuleError("Upload your photo before trying clothes on")
    if len(set(data.item_ids)) < len(data.item_ids):
        raise BusinessRuleError("The same item cannot be tried on twice")
    items = [items_service.get_item(db, item_id) for item_id in data.item_ids]
    categories = [item.category for item in items]
    if len(set(categories)) < len(categories):
        raise BusinessRuleError("Only one item per category can be tried on")
    photos = [storage.static_path(user.photo_url)] + [item_photo(item) for item in items]
    since = datetime.now(timezone.utc) - timedelta(days=1)
    used = db.scalar(select(func.count(TryOn.id)).where(TryOn.user_id == user_id, TryOn.created_at > since))
    if used >= DAILY_LIMIT:
        raise TooManyRequestsError(f"Daily limit reached: {DAILY_LIMIT} try-ons per day")
    mock = os.getenv("LLM_MOCK", "").lower() == "true"
    try_on = TryOn(user_id=user_id, items=items, status=TryOnStatus.failed, source="mock" if mock else "gemini")
    db.add(try_on)
    db.commit()
    if mock:
        result_url = f"/results/{try_on.id}{photos[0].suffix}"
        shutil.copy(photos[0], storage.static_path(result_url))
    else:
        try:
            image = await llm.generate_try_on(build_prompt(user, items), [encode_image(photo) for photo in photos])
        except LLMError as error:
            try_on.error = error.detail[:500]
            db.commit()
            raise
        result_url = f"/results/{try_on.id}.png"
        storage.static_path(result_url).write_bytes(image)
    try_on.status = TryOnStatus.done
    try_on.result_url = result_url
    db.commit()
    return try_on


def item_photo(item: Item) -> Path:
    path = storage.static_path(item.image_url or "").resolve()
    if not path.is_file() or storage.STATIC_DIR not in path.parents:
        raise BusinessRuleError(f"Item {item.id} has no photo for try-on")
    return path


def encode_image(path: Path) -> dict:
    return {
        "mime_type": mimetypes.guess_type(path.name)[0],
        "data": base64.b64encode(path.read_bytes()).decode(),
    }


def build_prompt(user: User, items: list[Item]) -> str:
    clothes = ", ".join(f"{item.name} ({item.color})" for item in items)
    return (
        "Одень человека с первого фото в вещи с остальных фото. Сохрани лицо, позу и фон.\n"
        f"Параметры человека: рост {user.height_cm} см, вес {user.weight_kg} кг, "
        f"тип фигуры {user.body_type}.\n"
        f"Вещи в порядке следования фото: {clothes}.\n"
        "Верни одно фотореалистичное изображение."
    )


def list_user_try_ons(db: Session, user_id: int) -> list[TryOn]:
    return users_service.get_user(db, user_id).try_ons


def get_try_on(db: Session, try_on_id: int) -> TryOn:
    try_on = db.get(TryOn, try_on_id)
    if try_on is None:
        raise NotFoundError(f"Try-on {try_on_id} not found")
    return try_on


def delete_try_on(db: Session, try_on_id: int) -> None:
    try_on = get_try_on(db, try_on_id)
    result_url = try_on.result_url
    db.delete(try_on)
    db.commit()
    storage.delete_file(result_url)
