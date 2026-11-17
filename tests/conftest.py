import os

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://zhibek:zhibek@localhost:5433/zhibek_test")
os.environ["LLM_MOCK"] = "true"

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
