from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import llm, seed
from app.exceptions import register_exception_handlers
from app.routers import fitting_room, items, orders, stylist, users

llm.load_env()  # GEMINI_API_KEY и LLM_MODEL из файла .env
seed.load_seed()  # стартовые товары и образы

app = FastAPI(title="Zhibek Lite", description="Учебный бэкенд сайта подбора одежды")
register_exception_handlers(app)

app.include_router(items.router)
app.include_router(users.router)
app.include_router(fitting_room.router)
app.include_router(orders.router)
app.include_router(stylist.router)

# фронт подключаем последним, чтобы он не перекрывал адреса API; static/index.html открывается по "/"
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
