import base64
import logging
import os

import httpx

from app.exceptions import LLMError

STUDIO_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
VERTEX_URL = "https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent"

logger = logging.getLogger("uvicorn.error")


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
    if os.getenv("GEMINI_BACKEND", "").lower() == "vertex":
        url = VERTEX_URL.format(model=model)
        auth = {"params": {"key": api_key}}
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": "3:4"},
            },
        }
    else:
        url = STUDIO_URL.format(model=model)
        auth = {"headers": {"x-goog-api-key": api_key}}
        body = {"contents": [{"parts": parts}]}

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, json=body, **auth)
        response.raise_for_status()
        answer_parts = response.json()["candidates"][0]["content"]["parts"]
    except httpx.HTTPStatusError as error:
        logger.error("Gemini %s: %s", error.response.status_code, error.response.text)
        raise LLMError(f"Gemini answered with status {error.response.status_code}")
    except Exception as error:
        raise LLMError(f"Gemini request failed: {type(error).__name__}")

    for part in answer_parts:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise LLMError("Gemini returned no image")
