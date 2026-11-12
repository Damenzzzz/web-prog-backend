from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.items import ItemOut


class StylistRequest(BaseModel):
    occasion: str = Field(min_length=3, max_length=200)
    budget: int | None = Field(None, gt=0)  # бюджет на весь образ


class LLMAnswer(BaseModel):
    # в таком виде LLM должна вернуть ответ
    item_ids: list[int]
    comment: str


class StylistResponse(BaseModel):
    items: list[ItemOut]
    comment: str
    total: int
    source: Literal["llm", "fallback"]
