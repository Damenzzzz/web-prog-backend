from pydantic import BaseModel, EmailStr, Field

from app.schemas.users import UserCreate


class RegisterIn(UserCreate):
    email: EmailStr
    # bcrypt учитывает только первые 72 байта пароля, поэтому длиннее не принимаем
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
