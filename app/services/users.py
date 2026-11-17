from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.exceptions import BusinessRuleError, ConflictError, NotFoundError, UnsupportedMediaError
from app.models import Order, User
from app.schemas.orders import OrderStatus
from app.schemas.users import UserCreate, UserUpdate

ACTIVE_STATUSES = [OrderStatus.pending, OrderStatus.paid]

MAX_PHOTO_BYTES = 5 * 1024 * 1024


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


def create_user(db: Session, data: UserCreate) -> User:
    user = User(**data.model_dump())
    db.add(user)
    db.commit()
    return user


def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
    user = get_user(db, user_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return user


def save_photo(db: Session, user_id: int, data: bytes) -> User:
    user = get_user(db, user_id)
    if data.startswith(b"\xff\xd8\xff"):
        extension = "jpg"
    elif data.startswith(b"\x89PNG"):
        extension = "png"
    else:
        raise UnsupportedMediaError("Only JPEG and PNG photos are allowed")
    if len(data) > MAX_PHOTO_BYTES:
        raise BusinessRuleError("Photo is larger than 5 MB")
    storage.delete_file(user.photo_url)
    user.photo_url = f"/uploads/user_{user_id}.{extension}"
    storage.static_path(user.photo_url).write_bytes(data)
    db.commit()
    return user


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)
    active = db.scalar(select(Order).where(Order.user_id == user_id, Order.status.in_(ACTIVE_STATUSES)))
    if active is not None:
        raise ConflictError(f"User {user_id} has active order {active.id} ({active.status})")
    files = [user.photo_url] + [try_on.result_url for try_on in user.try_ons]
    db.delete(user)
    db.commit()
    for url in files:
        storage.delete_file(url)
