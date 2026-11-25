from app.db import SessionLocal
from app.models import Item, Order, User
from tests.conftest import PASSWORD, PROFILE

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def test_catalog_seeded_with_looks(client):
    looks = client.get("/looks").json()
    assert len(looks) == 4
    assert looks[0]["item_ids"] == [1, 2, 3, 4]
    detail = client.get("/looks/2").json()
    assert {item["look_id"] for item in detail["items"]} == {2}
    shoes = client.get("/items", params={"category": "shoes", "in_stock": True}).json()
    assert shoes and all(item["category"] == "shoes" and item["stock"] > 0 for item in shoes)


def test_item_crud_and_errors(client, admin):
    h = admin["headers"]
    new = {"name": "Шарф", "category": "accessory", "color": "серый", "price": 9900, "stock": 3, "look_id": 1}
    created = client.post("/items", json=new, headers=h)
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert item_id in client.get("/looks/1").json()["item_ids"]
    assert client.patch(f"/items/{item_id}", json={"price": 8900, "look_id": None}, headers=h).json()["look_id"] is None
    assert client.post("/items", json={**new, "look_id": 999}, headers=h).status_code == 404
    assert client.post("/items", json={**new, "price": 0}, headers=h).status_code == 422
    assert client.patch(f"/items/{item_id}", json={"name": None}, headers=h).status_code == 400
    assert client.get("/items/999").status_code == 404
    assert client.delete(f"/items/{item_id}", headers=h).status_code == 204
    assert client.get(f"/items/{item_id}").status_code == 404


def test_cannot_delete_item_in_fitting_room(client, user, admin):
    client.post(f"/users/{user['id']}/fitting-room/items", json={"item_id": 1}, headers=user["headers"])
    response = client.delete("/items/1", headers=admin["headers"])
    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


def test_user_validation_and_missing(client, admin):
    base = {**PROFILE, "email": "new@example.com", "password": PASSWORD}
    assert client.post("/auth/register", json={**base, "height_cm": 50}).status_code == 422
    assert client.post("/auth/register", json={**base, "gender": "other"}).status_code == 422
    assert client.get("/users/999", headers=admin["headers"]).status_code == 404
    assert client.post("/users/999/fitting-room/items", json={"item_id": 1}, headers=admin["headers"]).status_code == 404


def test_fitting_room_rules(client, user):
    base = f"/users/{user['id']}/fitting-room"
    h = user["headers"]
    assert client.post(f"{base}/items", json={"item_id": 999}, headers=h).status_code == 404
    assert client.post(f"{base}/items", json={"item_id": 15}, headers=h).status_code == 400
    client.post(f"{base}/items", json={"item_id": 1, "quantity": 2}, headers=h)
    room = client.post(f"{base}/items", json={"item_id": 1}, headers=h).json()
    assert room["items"][0]["quantity"] == 3
    assert room["total"] == 3 * 21900
    assert client.patch(f"{base}/items/1", json={"quantity": 100}, headers=h).status_code == 400
    assert client.delete(f"{base}/items/2", headers=h).status_code == 404
    assert client.delete(f"{base}/items/1", headers=h).status_code == 204
    assert client.get(base, headers=h).json()["items"] == []


def test_order_flow_changes_stock(client, user, admin):
    user_id, h = user["id"], user["headers"]
    assert client.post(f"/users/{user_id}/orders", headers=h).status_code == 400
    client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 2, "quantity": 2}, headers=h)
    order = client.post(f"/users/{user_id}/orders", headers=h).json()
    assert order["total"] == 2 * 26900
    assert order["items"][0]["name"] == "Тёмно-синие классические брюки"
    assert client.get("/items/2").json()["stock"] == 6
    assert client.get(f"/users/{user_id}/fitting-room", headers=h).json()["items"] == []
    assert client.patch(f"/orders/{order['id']}/status", json={"status": "shipped"}, headers=admin["headers"]).status_code == 409
    assert client.patch(f"/orders/{order['id']}/status", json={"status": "cancelled"}, headers=h).json()["status"] == "cancelled"
    assert client.get("/items/2").json()["stock"] == 8
    assert client.get("/orders/999", headers=h).status_code == 404


def test_delete_user_rules_and_cascade(client, user, admin):
    user_id, h = user["id"], user["headers"]
    client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 3}, headers=h)
    order_id = client.post(f"/users/{user_id}/orders", headers=h).json()["id"]
    assert client.delete(f"/users/{user_id}", headers=h).status_code == 409
    client.patch(f"/orders/{order_id}/status", json={"status": "paid"}, headers=h)
    client.patch(f"/orders/{order_id}/status", json={"status": "shipped"}, headers=admin["headers"])
    assert client.delete(f"/users/{user_id}", headers=h).status_code == 204
    assert client.get(f"/orders/{order_id}", headers=admin["headers"]).status_code == 404


def test_data_is_stored_in_database(client, user):
    user_id, h = user["id"], user["headers"]
    client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 4}, headers=h)
    client.post(f"/users/{user_id}/orders", headers=h)
    with SessionLocal() as db:
        db_user = db.get(User, user_id)
        assert db_user.name == PROFILE["name"]
        assert len(db_user.orders) == 1
        assert isinstance(db_user.orders[0], Order)
        assert db.get(Item, 4).stock == 5


def test_try_on_mock_and_daily_limit(client, user):
    user_id, h = user["id"], user["headers"]
    assert client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1]}, headers=h).status_code == 400
    assert client.post(f"/users/{user_id}/photo", files={"file": ("a.txt", b"hello")}, headers=h).status_code == 415
    photo = client.post(f"/users/{user_id}/photo", files={"file": ("me.png", PNG)}, headers=h)
    assert photo.json()["photo_url"] == f"/uploads/user_{user_id}.png"
    assert client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1, 5]}, headers=h).status_code == 400
    for _ in range(3):
        response = client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1, 2]}, headers=h)
        assert response.status_code == 201
        assert response.json()["status"] == "done"
        assert response.json()["item_ids"] == [1, 2]
    assert client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1]}, headers=h).status_code == 429
    try_on_id = client.get(f"/users/{user_id}/try-ons", headers=h).json()[0]["id"]
    assert client.delete(f"/try-ons/{try_on_id}", headers=h).status_code == 204
    assert client.get(f"/try-ons/{try_on_id}", headers=h).status_code == 404
    assert len(client.get(f"/users/{user_id}/try-ons", headers=h).json()) == 2
    assert client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1]}, headers=h).status_code == 429
    assert client.delete(f"/users/{user_id}", headers=h).status_code == 204
