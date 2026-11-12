import base64
import os

import httpx

from app.exceptions import LLMError

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


async def generate_try_on(prompt: str, images: list[dict]) -> bytes:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LLMError("GEMINI_API_KEY is not set")

    model = os.getenv("LLM_MODEL", "gemini-2.5-flash-image")
    parts = [{"text": prompt}] + [{"inline_data": image} for image in images]
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                GEMINI_URL.format(model=model),
                headers={"x-goog-api-key": api_key},
                json={"contents": [{"parts": parts}]},
            )
        response.raise_for_status()
        answer_parts = response.json()["candidates"][0]["content"]["parts"]
    except httpx.HTTPStatusError as error:
        raise LLMError(f"Gemini answered with status {error.response.status_code}")
    except Exception as error:
        # сеть, таймаут, неожиданная структура ответа: сервер не падает, клиент получит 502
        raise LLMError(f"Gemini request failed: {type(error).__name__}")

    for part in answer_parts:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise LLMError("Gemini returned no image")
