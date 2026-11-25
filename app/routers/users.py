from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import ensure_owner_or_admin, get_current_user, require_admin
from app.models import User
from app.schemas.users import UserOut, UserUpdate
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["2. Профиль"])

# Создание пользователя теперь только через POST /auth/register.


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return users_service.list_users(db)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    return users_service.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    return users_service.update_user(db, user_id, data)


@router.post("/{user_id}/photo", response_model=UserOut)
async def upload_photo(user_id: int, file: UploadFile, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    data = await file.read(users_service.MAX_PHOTO_BYTES + 1)
    return users_service.save_photo(db, user_id, data)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    ensure_owner_or_admin(user_id, current_user)
    users_service.delete_user(db, user_id)
