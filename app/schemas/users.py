from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Gender(StrEnum):
    female = "female"
    male = "male"


class BodyType(StrEnum):
    slim = "slim"
    average = "average"
    athletic = "athletic"
    plus = "plus"


class Role(StrEnum):
    user = "user"
    admin = "admin"


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    height_cm: int = Field(ge=100, le=250)
    weight_kg: int = Field(ge=30, le=250)
    gender: Gender
    body_type: BodyType
    style_preference: str | None = Field(None, max_length=200)


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    height_cm: int | None = Field(None, ge=100, le=250)
    weight_kg: int | None = Field(None, ge=30, le=250)
    gender: Gender | None = None
    body_type: BodyType | None = None
    style_preference: str | None = Field(None, max_length=200)


class UserOut(UserCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: Role
    photo_url: str | None = None
