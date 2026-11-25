import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.llm import load_env

load_env()

# Секрет, которым подписывается токен. В .env должен быть свой длинный случайный.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-in-env-file-0000")
ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "60"))
MAX_PASSWORD_BYTES = 72  # предел bcrypt


def hash_password(password: str) -> str:
    # gensalt() даёт случайную соль, поэтому одинаковые пароли дают разные хеши
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    # такой пароль не мог быть сохранён при регистрации, значит он точно неверный
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# Хеш-пустышка: при входе с несуществующим email всё равно проверяем пароль,
# чтобы ответ шёл столько же времени и по скорости нельзя было понять, есть ли такой email.
DUMMY_HASH = hash_password("dummy-password")


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Возвращает id пользователя или None, если токен подделан, испорчен или просрочен."""
    try:
        # algorithms — только наш HS256 (подделку через "alg": "none" не примем),
        # require — токен без срока или без id считаем недействительным
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
