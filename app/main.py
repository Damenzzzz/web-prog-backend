from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import seed, storage
from app.db import SessionLocal
from app.exceptions import register_exception_handlers
from app.routers import auth, fitting_room, items, orders, try_on, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    for folder in ("uploads", "results"):
        (storage.STATIC_DIR / folder).mkdir(exist_ok=True)
    with SessionLocal() as db:
        seed.load_seed(db)
        seed.create_admin(db)
    yield


app = FastAPI(title="Zhibek Lite", description="Учебный бэкенд сайта подбора одежды", lifespan=lifespan)
register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(users.router)
app.include_router(fitting_room.router)
app.include_router(orders.router)
app.include_router(try_on.router)

app.mount("/", StaticFiles(directory=storage.STATIC_DIR, html=True), name="static")
