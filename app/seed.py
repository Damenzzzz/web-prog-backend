"""Стартовые данные: 4 образа и 15 товаров."""

from app import storage
from app.schemas.items import Category

LOOKS = [
    "Городская классика",
    "Выходные за городом",
    "Вечер в городе",
    "Офис без галстука",
]

# (название, категория, цвет, цена в тенге, остаток, id образа)
ITEMS = [
    ("Рубашка из хлопка", Category.top, "белый", 18900, 12, 1),
    ("Прямые брюки", Category.bottom, "бежевый", 24900, 8, 1),
    ("Классический тренч", Category.outerwear, "бежевый", 54900, 4, 1),
    ("Кожаные лоферы", Category.shoes, "коричневый", 39900, 6, 1),
    ("Свитер крупной вязки", Category.top, "терракотовый", 27900, 7, 2),
    ("Джинсы прямого кроя", Category.bottom, "синий", 22900, 10, 2),
    ("Стёганая куртка", Category.outerwear, "оливковый", 46900, 5, 2),
    ("Кеды из канваса", Category.shoes, "белый", 19900, 9, 2),
    ("Шёлковый топ", Category.top, "чёрный", 21900, 6, 3),
    ("Юбка миди", Category.bottom, "терракотовый", 26900, 5, 3),
    ("Сумка-багет", Category.bag, "чёрный", 32900, 3, 3),
    ("Жакет оверсайз", Category.outerwear, "серый", 49900, 4, 4),
    ("Водолазка из мериноса", Category.top, "серый", 23900, 6, 4),
    ("Брюки со стрелками", Category.bottom, "чёрный", 28900, 7, 4),
    ("Шёлковый платок", Category.accessory, "терракотовый", 9900, 0, None),  # нет в наличии
]


def load_seed() -> None:
    for title in LOOKS:
        look_id = storage.next_id("look")
        storage.looks[look_id] = {"id": look_id, "title": title}

    for name, category, color, price, stock, look_id in ITEMS:
        item_id = storage.next_id("item")
        storage.items[item_id] = {
            "id": item_id,
            "name": name,
            "category": category,
            "color": color,
            "price": price,
            "stock": stock,
            "look_id": look_id,
            "image_url": None,
        }
