from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, UnauthorizedError
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn
from app.security import DUMMY_HASH, create_access_token, hash_password, verify_password


def find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def register(db: Session, data: RegisterIn) -> User:
    if find_by_email(db, data.email) is not None:
        raise ConflictError("User with this email already exists")
    profile = data.model_dump(exclude={"email", "password"})
    # роль не берём из запроса: регистрация всегда создаёт обычного пользователя
    user = User(**profile, email=data.email.lower(), password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    return user


def login(db: Session, data: LoginIn) -> str:
    user = find_by_email(db, data.email)
    # одно сообщение и одинаковое время для «нет такого email» и «неверный пароль»,
    # чтобы по ответу нельзя было узнать, какие email зарегистрированы
    password_ok = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise UnauthorizedError("Invalid email or password")
    return create_access_token(user.id)
