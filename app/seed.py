from app import storage
from app.schemas.items import Category

LOOKS = [
    "Офисная классика",
    "Бордовый вечер",
    "Выходные в городе",
    "Прогулка в парке",
]

ITEMS = [
    ("Кремовая шёлковая блузка", Category.top, "бежевый", 21900, 12, 1, "1-3.jpg"),
    ("Тёмно-синие классические брюки", Category.bottom, "синий", 26900, 8, 1, "1-1.jpg"),
    ("Тёмно-синий костюмный жилет", Category.outerwear, "синий", 29900, 4, 1, "1-2.jpg"),
    ("Бежевые туфли-лодочки", Category.shoes, "бежевый", 34900, 6, 1, "1-4.jpg"),
    ("Розовая блузка с бантом", Category.top, "розовый", 19900, 7, 2, "3-3.jpg"),
    ("Бордовая юбка-карандаш", Category.bottom, "бордовый", 23900, 5, 2, "3-2.jpg"),
    ("Бордовый приталенный жакет", Category.outerwear, "бордовый", 44900, 5, 2, "3-1.jpg"),
    ("Бордовая сумка на плечо", Category.bag, "бордовый", 31900, 4, 2, "3-5.jpg"),
    ("Белая хлопковая рубашка", Category.top, "белый", 17900, 9, 3, "6-1.jpg"),
    ("Голубой вязаный жилет", Category.outerwear, "голубой", 24900, 6, 3, "6-2.jpg"),
    ("Белые кожаные кроссовки", Category.shoes, "белый", 32900, 3, 3, "6-4.jpg"),
    ("Зелёный вязаный джемпер", Category.top, "зелёный", 25900, 6, 4, "7-1.jpg"),
    ("Бежевая плиссированная юбка", Category.bottom, "бежевый", 22900, 7, 4, "7-3.jpg"),
    ("Чёрные туфли-лодочки", Category.shoes, "чёрный", 36900, 5, 4, "5-3.jpg"),
    ("Серо-зелёная кожаная сумка", Category.bag, "зелёный", 38900, 0, 4, "7-5.jpg"),
]


def load_seed() -> None:
    for title in LOOKS:
        look_id = storage.next_id("look")
        storage.looks[look_id] = {"id": look_id, "title": title}

    for name, category, color, price, stock, look_id, photo in ITEMS:
        item_id = storage.next_id("item")
        storage.items[item_id] = {
            "id": item_id,
            "name": name,
            "category": category,
            "color": color,
            "price": price,
            "stock": stock,
            "look_id": look_id,
            "image_url": f"/catalog/{photo}",
        }
