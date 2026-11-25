from datetime import datetime, timedelta, timezone

import jwt

from app.db import SessionLocal
from app.models import User
from app.security import ALGORITHM, SECRET_KEY, create_access_token
from tests.conftest import PASSWORD, PROFILE

NEW = {**PROFILE, "email": "Aigerim@Example.com", "password": PASSWORD}


# ---------- регистрация ----------

def test_register_creates_user_with_hashed_password(client):
    response = client.post("/auth/register", json=NEW)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "aigerim@example.com"  # email приводится к нижнему регистру
    assert body["role"] == "user"
    assert "password" not in body and "password_hash" not in body
    with SessionLocal() as db:
        stored = db.get(User, body["id"]).password_hash
    assert stored != PASSWORD
    assert stored.startswith("$2b$")  # формат bcrypt


def test_register_duplicate_email(client):
    assert client.post("/auth/register", json=NEW).status_code == 201
    response = client.post("/auth/register", json={**NEW, "email": "aigerim@example.com"})
    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


def test_register_validation(client):
    assert client.post("/auth/register", json={**NEW, "email": "not-an-email"}).status_code == 422
    assert client.post("/auth/register", json={**NEW, "password": "short"}).status_code == 422
    assert client.post("/auth/register", json={**NEW, "password": "x" * 73}).status_code == 422


def test_register_cannot_make_admin(client):
    response = client.post("/auth/register", json={**NEW, "role": "admin"})
    assert response.status_code == 201
    assert response.json()["role"] == "user"


# ---------- вход ----------

def test_login_returns_token(client):
    user_id = client.post("/auth/register", json=NEW).json()["id"]
    response = client.post("/auth/login", json={"email": "aigerim@example.com", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == user_id


def test_login_invalid_credentials(client):
    client.post("/auth/register", json=NEW)
    wrong_password = client.post("/auth/login", json={"email": NEW["email"], "password": "wrong-password"})
    unknown_email = client.post("/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # одинаковый ответ: нельзя понять, существует ли такой email
    assert wrong_password.json() == unknown_email.json()


# ---------- токен ----------

def test_protected_endpoint_without_token(client, user):
    response = client.get(f"/users/{user['id']}/fitting-room")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert client.get("/auth/me").status_code == 401


def test_protected_endpoint_with_bad_tokens(client, user):
    url = f"/users/{user['id']}/fitting-room"
    garbage = {"Authorization": "Bearer abc.def.ghi"}
    expired = jwt.encode({"sub": str(user["id"]), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, SECRET_KEY, ALGORITHM)
    forged = jwt.encode({"sub": str(user["id"])}, "someone-else-secret-that-we-do-not-know", ALGORITHM)
    assert client.get(url, headers=garbage).status_code == 401
    assert client.get(url, headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get(url, headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    assert client.get(url, headers=user["headers"]).status_code == 200


def test_token_of_deleted_user(client, user):
    token = create_access_token(user["id"])
    assert client.delete(f"/users/{user['id']}", headers=user["headers"]).status_code == 204
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_public_endpoints_need_no_token(client):
    assert client.get("/items").status_code == 200
    assert client.get("/looks").status_code == 200


# ---------- права: чужие ресурсы ----------

def test_user_cannot_touch_other_users_data(client, user, other_user):
    victim, h = user["id"], other_user["headers"]
    assert client.get(f"/users/{victim}", headers=h).status_code == 403
    assert client.patch(f"/users/{victim}", json={"name": "Хакер"}, headers=h).status_code == 403
    assert client.delete(f"/users/{victim}", headers=h).status_code == 403
    assert client.get(f"/users/{victim}/fitting-room", headers=h).status_code == 403
    assert client.post(f"/users/{victim}/fitting-room/items", json={"item_id": 1}, headers=h).status_code == 403
    assert client.get(f"/users/{victim}/orders", headers=h).status_code == 403
    assert client.post(f"/users/{victim}/orders", headers=h).status_code == 403
    assert client.get(f"/users/{victim}/try-ons", headers=h).status_code == 403
    response = client.get(f"/users/{victim}", headers=h)
    assert response.json()["error"] == "forbidden"
    # данные жертвы не изменились
    assert client.get(f"/users/{victim}", headers=user["headers"]).json()["name"] == PROFILE["name"]


def test_user_cannot_see_or_change_other_users_order(client, user, other_user):
    h = user["headers"]
    client.post(f"/users/{user['id']}/fitting-room/items", json={"item_id": 1}, headers=h)
    order_id = client.post(f"/users/{user['id']}/orders", headers=h).json()["id"]
    assert client.get(f"/orders/{order_id}", headers=other_user["headers"]).status_code == 403
    response = client.patch(f"/orders/{order_id}/status", json={"status": "cancelled"}, headers=other_user["headers"])
    assert response.status_code == 403
    assert client.get(f"/orders/{order_id}", headers=h).json()["status"] == "pending"


def test_user_cannot_delete_other_users_try_on(client, user, other_user):
    h = user["headers"]
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    client.post(f"/users/{user['id']}/photo", files={"file": ("me.png", png)}, headers=h)
    try_on_id = client.post(f"/users/{user['id']}/try-ons", json={"item_ids": [1]}, headers=h).json()["id"]
    assert client.get(f"/try-ons/{try_on_id}", headers=other_user["headers"]).status_code == 403
    assert client.delete(f"/try-ons/{try_on_id}", headers=other_user["headers"]).status_code == 403
    assert client.get(f"/try-ons/{try_on_id}", headers=h).status_code == 200


# ---------- права: роли ----------

def test_only_admin_manages_catalog(client, user, admin):
    new = {"name": "Шарф", "category": "accessory", "color": "серый", "price": 9900, "stock": 3}
    assert client.post("/items", json=new).status_code == 401
    assert client.post("/items", json=new, headers=user["headers"]).status_code == 403
    assert client.patch("/items/1", json={"price": 1}, headers=user["headers"]).status_code == 403
    assert client.delete("/items/1", headers=user["headers"]).status_code == 403
    assert client.get("/items/1").json()["price"] == 21900
    assert client.post("/items", json=new, headers=admin["headers"]).status_code == 201


def test_only_admin_lists_users(client, user, admin):
    assert client.get("/users", headers=user["headers"]).status_code == 403
    response = client.get("/users", headers=admin["headers"])
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_admin_can_access_any_user(client, user, admin):
    assert client.get(f"/users/{user['id']}", headers=admin["headers"]).status_code == 200
    assert client.get(f"/users/{user['id']}/orders", headers=admin["headers"]).status_code == 200


def test_order_status_rules_by_role(client, user, admin):
    h = user["headers"]
    client.post(f"/users/{user['id']}/fitting-room/items", json={"item_id": 1}, headers=h)
    order_id = client.post(f"/users/{user['id']}/orders", headers=h).json()["id"]
    assert client.patch(f"/orders/{order_id}/status", json={"status": "paid"}, headers=h).status_code == 200
    # отправляет заказ только магазин
    assert client.patch(f"/orders/{order_id}/status", json={"status": "shipped"}, headers=h).status_code == 403
    assert client.patch(f"/orders/{order_id}/status", json={"status": "shipped"}, headers=admin["headers"]).status_code == 200


# ---------- найдено при осмотре ----------

def test_cyrillic_password_and_byte_limit(client):
    # 36 букв кириллицы = 72 байта — ровно предел bcrypt, должно работать
    cyrillic = "пароль" * 6
    assert client.post("/auth/register", json={**NEW, "password": cyrillic}).status_code == 201
    assert client.post("/auth/login", json={"email": NEW["email"], "password": cyrillic}).status_code == 200
    # 42 буквы = 84 байта: раньше был 500, теперь понятная 422
    too_long = {**NEW, "email": "long@example.com", "password": "пароль" * 7}
    assert client.post("/auth/register", json=too_long).status_code == 422
    # длинный пароль при входе — просто неверный пароль, а не 500
    assert client.post("/auth/login", json={"email": NEW["email"], "password": "я" * 50}).status_code == 401


def test_token_without_expiration_is_rejected(client, user):
    no_exp = jwt.encode({"sub": str(user["id"])}, SECRET_KEY, ALGORITHM)
    no_sub = jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, SECRET_KEY, ALGORITHM)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {no_exp}"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {no_sub}"}).status_code == 401


def test_401_says_how_to_authenticate(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
