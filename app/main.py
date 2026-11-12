import shutil

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import llm, seed, storage
from app.exceptions import register_exception_handlers
from app.routers import fitting_room, items, orders, try_on, users

llm.load_env()
seed.load_seed()

# данные живут в памяти, поэтому фото и результаты прошлого запуска тоже стираем
for folder in ("uploads", "results"):
    shutil.rmtree(storage.STATIC_DIR / folder, ignore_errors=True)
    (storage.STATIC_DIR / folder).mkdir()

app = FastAPI(title="Zhibek Lite", description="Учебный бэкенд сайта подбора одежды")
register_exception_handlers(app)

app.include_router(items.router)
app.include_router(users.router)
app.include_router(fitting_room.router)
app.include_router(orders.router)
app.include_router(try_on.router)

app.mount("/", StaticFiles(directory=storage.STATIC_DIR, html=True), name="static")
