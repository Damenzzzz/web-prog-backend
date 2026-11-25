from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.users import UserCreate
from app.security import MAX_PASSWORD_BYTES


class RegisterIn(UserCreate):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        # bcrypt принимает максимум 72 байта. Буква кириллицы — 2 байта, поэтому считаем байты, а не символы.
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password is too long: maximum {MAX_PASSWORD_BYTES} bytes")
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
