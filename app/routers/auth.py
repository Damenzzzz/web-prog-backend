from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut
from app.schemas.users import UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["0. Регистрация и вход"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    return auth_service.register(db, data)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    return TokenOut(access_token=auth_service.login(db, data))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
