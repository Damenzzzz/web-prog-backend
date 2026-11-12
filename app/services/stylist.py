"""Workflow 4: AI-стилист. Спрашиваем LLM, ответ проверяем, при любой проблеме — подбор по правилам."""

import json

from pydantic import ValidationError

from app import llm, storage
from app.schemas.items import Category
from app.schemas.stylist import LLMAnswer, StylistRequest
from app.services import items as items_service
from app.services import users as users_service

FALLBACK_COMMENT = "Стилист сейчас недоступен, поэтому образ собран по правилам сочетания категорий и цветов."
EMPTY_COMMENT = "В этот бюджет не укладывается ни один товар в наличии."


async def suggest_outfit(user_id: int, data: StylistRequest) -> dict:
    user = users_service.get_user(user_id)
    available = items_service.list_items(in_stock=True)

    text = await llm.ask_llm(build_prompt(user, available, data))
    answer = parse_answer(text)

    if answer is not None:
        # LLM могла придумать id или выбрать закончившийся товар — оставляем только настоящие
        chosen = []
        for item_id in answer.item_ids:
            item = storage.items.get(item_id)
            if item is not None and item["stock"] > 0 and item not in chosen:
                chosen.append(item)
        chosen = fit_budget(chosen, data.budget)
        if chosen:
            return make_response(chosen, answer.comment, "llm")

    # LLM недоступна, вернула битый JSON или ни одного подходящего товара
    chosen = fit_budget(fallback_outfit(data.budget), data.budget)
    return make_response(chosen, FALLBACK_COMMENT if chosen else EMPTY_COMMENT, "fallback")


def build_prompt(user: dict, available: list[dict], data: StylistRequest) -> str:
    catalog = [
        {"id": i["id"], "name": i["name"], "category": i["category"], "color": i["color"], "price": i["price"]}
        for i in available
    ]
    budget = f"{data.budget} тенге на весь образ" if data.budget else "не ограничен"
    return (
        "Ты стилист магазина одежды. Собери из каталога один образ из 3-5 вещей.\n"
        f"Клиент: {user['name']}, пол {user['gender']}, рост {user['height_cm']} см, "
        f"вес {user['weight_kg']} кг, тип фигуры {user['body_type']}, "
        f"предпочтения в стиле: {user['style_preference'] or 'не указаны'}.\n"
        f"Повод: {data.occasion}\n"
        f"Бюджет: {budget}.\n"
        f"Каталог (только товары в наличии): {json.dumps(catalog, ensure_ascii=False)}\n"
        "Ответь строго в формате JSON без пояснений: "
        '{"item_ids": [id товаров из каталога], "comment": "1-2 предложения на русском, почему образ подходит"}'
    )


def parse_answer(text: str | None) -> LLMAnswer | None:
    if text is None:
        return None
    # LLM может обернуть JSON в ```json ... ``` — берём кусок от первой { до последней }
    json_part = text[text.find("{") : text.rfind("}") + 1]
    try:
        return LLMAnswer.model_validate_json(json_part)
    except ValidationError:
        return None  # битый JSON или не те поля


def fit_budget(items: list[dict], budget: int | None) -> list[dict]:
    """Оставить вещи, которые по сумме укладываются в бюджет."""
    if budget is None:
        return items
    result = []
    total = 0
    for item in items:
        if total + item["price"] <= budget:
            result.append(item)
            total += item["price"]
    return result


def fallback_outfit(budget: int | None) -> list[dict]:
    """Образ по правилам workflow 1: берём верх и дополняем его сочетающимися вещами."""
    affordable = items_service.list_items(in_stock=True, max_price=budget)
    if not affordable:
        return []
    tops = [item for item in affordable if item["category"] == Category.top]
    base = tops[0] if tops else affordable[0]
    return [base] + items_service.find_matches(base["id"], limit=3)


def make_response(items: list[dict], comment: str, source: str) -> dict:
    return {
        "items": items,
        "comment": comment,
        "total": sum(item["price"] for item in items),
        "source": source,
    }
