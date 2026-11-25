from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.exceptions import ForbiddenError, UnauthorizedError
from app.models import User
from app.schemas.users import Role
from app.security import decode_access_token

# Читает заголовок "Authorization: Bearer <token>" и добавляет кнопку Authorize в Swagger.
# auto_error=False: если заголовка нет, не падаем сами, а отвечаем 401 в общем формате ошибок.
bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise UnauthorizedError("Invalid or expired token")
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User of this token no longer exists")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != Role.admin:
        raise ForbiddenError("Admin role required")
    return current_user


def ensure_owner_or_admin(owner_id: int, current_user: User) -> None:
    """Пускает владельца ресурса и админа, остальным 403."""
    if current_user.id != owner_id and current_user.role != Role.admin:
        raise ForbiddenError("You can access only your own resources")
