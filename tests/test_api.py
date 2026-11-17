from app.db import SessionLocal
from app.models import Item, Order, User

USER = {"name": "Айгерим", "height_cm": 165, "weight_kg": 55, "gender": "female", "body_type": "slim"}

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def create_user(client) -> int:
    response = client.post("/users", json=USER)
    assert response.status_code == 201
    return response.json()["id"]


def test_catalog_seeded_with_looks(client):
    looks = client.get("/looks").json()
    assert len(looks) == 4
    assert looks[0]["item_ids"] == [1, 2, 3, 4]
    detail = client.get("/looks/2").json()
    assert {item["look_id"] for item in detail["items"]} == {2}
    shoes = client.get("/items", params={"category": "shoes", "in_stock": True}).json()
    assert shoes and all(item["category"] == "shoes" and item["stock"] > 0 for item in shoes)


def test_item_crud_and_errors(client):
    new = {"name": "Шарф", "category": "accessory", "color": "серый", "price": 9900, "stock": 3, "look_id": 1}
    created = client.post("/items", json=new)
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert item_id in client.get("/looks/1").json()["item_ids"]
    assert client.patch(f"/items/{item_id}", json={"price": 8900, "look_id": None}).json()["look_id"] is None
    assert client.post("/items", json={**new, "look_id": 999}).status_code == 404
    assert client.post("/items", json={**new, "price": 0}).status_code == 422
    assert client.patch(f"/items/{item_id}", json={"name": None}).status_code == 400
    assert client.get("/items/999").status_code == 404
    assert client.delete(f"/items/{item_id}").status_code == 204
    assert client.get(f"/items/{item_id}").status_code == 404


def test_cannot_delete_item_in_fitting_room(client):
    user_id = create_user(client)
    client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 1})
    response = client.delete("/items/1")
    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


def test_user_validation_and_missing(client):
    assert client.post("/users", json={**USER, "height_cm": 50}).status_code == 422
    assert client.post("/users", json={**USER, "gender": "other"}).status_code == 422
    assert client.get("/users/999").status_code == 404
    assert client.post("/users/999/fitting-room/items", json={"item_id": 1}).status_code == 404


def test_fitting_room_rules(client):
    user_id = create_user(client)
    assert client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 999}).status_code == 404
    assert client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 15}).status_code == 400
    client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 1, "quantity": 2})
    room = client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 1}).json()
    assert room["items"][0]["quantity"] == 3
    assert room["total"] == 3 * 21900
    assert client.patch(f"/users/{user_id}/fitting-room/items/1", json={"quantity": 100}).status_code == 400
    assert client.delete(f"/users/{user_id}/fitting-room/items/2").status_code == 404
    assert client.delete(f"/users/{user_id}/fitting-room/items/1").status_code == 204
    assert client.get(f"/users/{user_id}/fitting-room").json()["items"] == []


def test_order_flow_changes_stock(client):
    user_id = create_user(client)
    assert client.post(f"/users/{user_id}/orders").status_code == 400
    client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 2, "quantity": 2})
    order = client.post(f"/users/{user_id}/orders").json()
    assert order["total"] == 2 * 26900
    assert order["items"][0]["name"] == "Тёмно-синие классические брюки"
    assert client.get("/items/2").json()["stock"] == 6
    assert client.get(f"/users/{user_id}/fitting-room").json()["items"] == []
    assert client.patch(f"/orders/{order['id']}/status", json={"status": "shipped"}).status_code == 409
    assert client.patch(f"/orders/{order['id']}/status", json={"status": "cancelled"}).json()["status"] == "cancelled"
    assert client.get("/items/2").json()["stock"] == 8
    assert client.get("/orders/999").status_code == 404


def test_delete_user_rules_and_cascade(client):
    user_id = create_user(client)
    client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 3})
    order_id = client.post(f"/users/{user_id}/orders").json()["id"]
    assert client.delete(f"/users/{user_id}").status_code == 409
    client.patch(f"/orders/{order_id}/status", json={"status": "paid"})
    client.patch(f"/orders/{order_id}/status", json={"status": "shipped"})
    assert client.delete(f"/users/{user_id}").status_code == 204
    assert client.get(f"/orders/{order_id}").status_code == 404


def test_data_is_stored_in_database(client):
    user_id = create_user(client)
    client.post(f"/users/{user_id}/fitting-room/items", json={"item_id": 4})
    client.post(f"/users/{user_id}/orders")
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user.name == USER["name"]
        assert len(user.orders) == 1
        assert isinstance(user.orders[0], Order)
        assert db.get(Item, 4).stock == 5


def test_try_on_mock_and_daily_limit(client):
    user_id = create_user(client)
    assert client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1]}).status_code == 400
    assert client.post(f"/users/{user_id}/photo", files={"file": ("a.txt", b"hello")}).status_code == 415
    assert client.post(f"/users/{user_id}/photo", files={"file": ("me.png", PNG)}).json()["photo_url"] == f"/uploads/user_{user_id}.png"
    assert client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1, 5]}).status_code == 400
    for _ in range(3):
        response = client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1, 2]})
        assert response.status_code == 201
        assert response.json()["status"] == "done"
        assert response.json()["item_ids"] == [1, 2]
    assert client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1]}).status_code == 429
    try_on_id = client.get(f"/users/{user_id}/try-ons").json()[0]["id"]
    assert client.delete(f"/try-ons/{try_on_id}").status_code == 204
    assert client.get(f"/try-ons/{try_on_id}").status_code == 404
    assert len(client.get(f"/users/{user_id}/try-ons").json()) == 2
    assert client.post(f"/users/{user_id}/try-ons", json={"item_ids": [1]}).status_code == 429
    assert client.delete(f"/users/{user_id}").status_code == 204
