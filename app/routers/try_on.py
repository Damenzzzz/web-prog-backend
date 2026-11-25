from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import ensure_owner_or_admin, get_current_user
from app.models import User
from app.schemas.try_on import TryOnCreate, TryOnOut
from app.services import try_on as try_on_service

router = APIRouter(tags=["4. AI-примерка"])


@router.post("/users/{user_id}/try-ons", response_model=TryOnOut, status_code=201)
async def create_try_on(user_id: int, data: TryOnCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    return await try_on_service.create_try_on(db, user_id, data)


@router.get("/users/{user_id}/try-ons", response_model=list[TryOnOut])
def list_user_try_ons(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_owner_or_admin(user_id, current_user)
    return try_on_service.list_user_try_ons(db, user_id)


@router.get("/try-ons/{try_on_id}", response_model=TryOnOut)
def get_try_on(try_on_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try_on = try_on_service.get_try_on(db, try_on_id)
    ensure_owner_or_admin(try_on.user_id, current_user)
    return try_on


@router.delete("/try-ons/{try_on_id}", status_code=204)
def delete_try_on(try_on_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    try_on = try_on_service.get_try_on(db, try_on_id)
    ensure_owner_or_admin(try_on.user_id, current_user)
    try_on_service.delete_try_on(db, try_on_id)
