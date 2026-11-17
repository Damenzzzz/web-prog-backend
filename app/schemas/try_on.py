from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TryOnStatus(StrEnum):
    done = "done"
    failed = "failed"


class TryOnCreate(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=3)


class TryOnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    item_ids: list[int]
    status: TryOnStatus
    source: Literal["gemini", "mock"]
    result_url: str | None
    error: str | None
    created_at: datetime
