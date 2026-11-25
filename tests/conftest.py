import os

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://zhibek:zhibek@localhost:5433/zhibek_test")
os.environ["LLM_MOCK"] = "true"
os.environ["ADMIN_EMAIL"] = ""  # админа из .env в тестах не создаём, тесты делают своего

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from alembic import command
from app.db import Base, engine
from app.main import app


def create_test_database():
    admin = create_engine(engine.url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": engine.url.database})
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{engine.url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def database():
    create_test_database()
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture
def client():
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    with TestClient(app) as test_client:
        yield test_client


PROFILE = {"name": "Айгерим", "height_cm": 165, "weight_kg": 55, "gender": "female", "body_type": "slim"}
PASSWORD = "secret123"


def register(client, email: str) -> int:
    response = client.post("/auth/register", json={**PROFILE, "email": email, "password": PASSWORD})
    assert response.status_code == 201
    return response.json()["id"]


def auth_headers(client, email: str) -> dict:
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def user(client) -> dict:
    """Обычный пользователь: его id и готовый заголовок с токеном."""
    user_id = register(client, "user@example.com")
    return {"id": user_id, "headers": auth_headers(client, "user@example.com")}


@pytest.fixture
def other_user(client) -> dict:
    user_id = register(client, "other@example.com")
    return {"id": user_id, "headers": auth_headers(client, "other@example.com")}


@pytest.fixture
def admin(client) -> dict:
    """Через API админа не создать, поэтому регистрируем обычного и меняем роль прямо в базе."""
    user_id = register(client, "admin@example.com")
    with engine.begin() as connection:
        connection.execute(text("UPDATE users SET role = 'admin' WHERE id = :id"), {"id": user_id})
    return {"id": user_id, "headers": auth_headers(client, "admin@example.com")}
