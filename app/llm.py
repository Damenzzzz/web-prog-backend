"""Единственное место, где приложение ходит в LLM (Gemini API)."""

import os

import httpx

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def load_env(path: str = ".env") -> None:
    """Прочитать .env без сторонних библиотек: строки вида KEY=VALUE."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


async def ask_llm(prompt: str) -> str | None:
    """Вернуть текст ответа LLM или None, если LLM недоступна."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None  # ключа нет — сервис сразу уйдёт в fallback

    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                GEMINI_URL.format(model=model),
                headers={"x-goog-api-key": api_key},
                json=body,
            )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        # сеть, таймаут, 4xx/5xx, неожиданная структура ответа — всё это не должно ронять сервер
        return None
