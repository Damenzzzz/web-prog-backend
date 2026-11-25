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


def hash_password(password: str) -> str:
    # gensalt() даёт случайную соль, поэтому одинаковые пароли дают разные хеши
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Возвращает id пользователя или None, если токен подделан, испорчен или просрочен."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
