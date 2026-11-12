from fastapi import APIRouter, UploadFile

from app.schemas.users import UserCreate, UserOut, UserUpdate
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["2. Профиль"])


@router.get("", response_model=list[UserOut])
async def list_users():
    return users_service.list_users()


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int):
    return users_service.get_user(user_id)


@router.post("", response_model=UserOut, status_code=201)
async def create_user(data: UserCreate):
    return users_service.create_user(data)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, data: UserUpdate):
    return users_service.update_user(user_id, data)


@router.post("/{user_id}/photo", response_model=UserOut)
async def upload_photo(user_id: int, file: UploadFile):
    # читаем на 1 байт больше лимита, чтобы сервис увидел превышение размера
    data = await file.read(users_service.MAX_PHOTO_BYTES + 1)
    return users_service.save_photo(user_id, data)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int) -> None:
    users_service.delete_user(user_id)
