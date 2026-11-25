# Zhibek Lite

Учебный проект по веб-программированию: минимальный бэкенд на FastAPI и лёгкий фронт для сайта подбора одежды
с AI-примеркой. Данные хранятся в PostgreSQL (SQLAlchemy + Alembic) и не теряются при перезапуске.

## Запуск

Проще всего всё поднять в Docker (см. ниже). Локально нужна только база из compose:

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d db          # PostgreSQL на localhost:5433
alembic upgrade head             # создать таблицы по миграциям
uvicorn app.main:app --reload
```

- Сайт: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

При первом старте, если таблица `looks` пустая, `seed.py` заполняет каталог (4 образа, 15 товаров).

### Переменные окружения

Скопируйте `.env.example` в `.env`. Ключ читается только из `.env` (или из окружения), в коде его нет.

| Переменная | По умолчанию | Зачем |
|---|---|---|
| `GEMINI_API_KEY` | пусто | ключ Gemini API для AI-примерки; без него примерка отвечает 502 |
| `LLM_MODEL` | `gemini-2.5-flash-image` | модель, которая генерирует картинку |
| `LLM_MOCK` | `false` | `true` — Gemini не вызывается, результатом примерки становится копия фото пользователя |
| `DATABASE_URL` | `postgresql+psycopg://zhibek:zhibek@localhost:5433/zhibek` | строка подключения к PostgreSQL; в compose подставляется сама |
| `SECRET_KEY` | тестовая строка | секрет для подписи JWT; в `.env` нужен свой длинный случайный (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `TOKEN_MINUTES` | `60` | сколько минут действует токен |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | пусто | если заданы, при старте создаётся админ (через регистрацию админом стать нельзя) |
| `GEMINI_BACKEND` | пусто | `vertex` — ключ от Vertex AI (Google Cloud): запрос идёт на `aiplatform.googleapis.com`, ключ передаётся в `?key=`; пусто — ключ Google AI Studio |

Без ключа удобно проверять всё остальное с `LLM_MOCK=true`.

### Запуск в Docker

```bash
cp .env.example .env            # вписать ключ или LLM_MOCK=true
docker compose up -d --build
```

Поднимаются два контейнера проекта `zhibek-lite`:

- `zhibek-lite-db` — PostgreSQL 16, данные в volume `pgdata`, снаружи порт 5433;
- `zhibek-lite` — приложение. При старте выполняет `alembic upgrade head`, потом запускает uvicorn. Сайт: http://127.0.0.1:8090.

Фото пользователей и результаты примерок лежат в volume `uploads` и `results`, поэтому тоже переживают перезапуск.
`docker compose down` останавливает всё, `docker compose down -v` ещё и стирает базу.

## База данных

```
looks 1 ──< items >── try_on_items ──< try_ons >── 1 users
              │                                     │
              └──< fitting_room_rows >──────────────┤
              └──< order_items >── orders >─────────┘
```

| Таблица | Связи | Ограничения |
|---|---|---|
| `looks` | один образ → много `items` | `title` уникален |
| `items` | `look_id` → `looks` (`ON DELETE SET NULL`) | `price > 0`, `stock >= 0`, `category` — enum |
| `users` | один пользователь → много строк примерочной, заказов, примерок | `email` уникален, `password_hash` (bcrypt), `role` — enum `user`/`admin`; рост 100–250, вес 30–250, `gender`/`body_type` — enum |
| `fitting_room_rows` | `user_id` → `users` (`CASCADE`), `item_id` → `items` (`RESTRICT`) | `UNIQUE(user_id, item_id)`, `quantity >= 1` |
| `orders` | `user_id` → `users` (`CASCADE`); один заказ → много `order_items` | `total >= 0`, `status` — enum |
| `order_items` | `order_id` → `orders` (`CASCADE`), `item_id` → `items` (`SET NULL`) | снапшот `name` и `price` на момент заказа |
| `try_ons` | `user_id` → `users` (`CASCADE`), многие-ко-многим с `items` через `try_on_items` | `deleted_at` — мягкое удаление |

Почему так:

- товар из примерочной удалить нельзя (`RESTRICT` + проверка в сервисе → 409), а товар из старого заказа можно — в заказе
  остаются название и цена, `item_id` становится `null`;
- при удалении пользователя база сама удаляет его примерочную, заказы и примерки (`ON DELETE CASCADE`);
- примерка удаляется мягко: строка остаётся, чтобы считать дневной лимит, но из API она пропадает;
- если запрос всё-таки нарушит ограничение базы, `IntegrityError` превращается в ответ 409 `conflict`.

Миграции лежат в `alembic/versions/`:

1. `initial schema` — все таблицы, ключи, индексы и ограничения;
2. `soft delete for try-ons` — колонка `try_ons.deleted_at`;
3. `auth for users` — колонки `users.email` (UNIQUE), `users.password_hash`, `users.role`. Старые анкеты без email и пароля
   удаляются (войти в них всё равно нельзя), их данные уходят по `ON DELETE CASCADE`.

```bash
alembic upgrade head               # применить все
alembic downgrade base             # откатить всё (enum-типы тоже удаляются)
alembic revision --autogenerate -m "..."   # новая миграция после изменения app/models.py
```

Сессия: `app/db.py` → `get_db()` открывает `Session` на один запрос и закрывает её в `finally`. Роутеры получают её через
`Depends(get_db)` и передают в сервисы, `commit` делают сервисы. Оформление заказа идёт одной транзакцией и блокирует строки
товаров (`SELECT ... FOR UPDATE`), чтобы два заказа одновременно не списали один остаток.

## Тесты

```bash
pip install -r requirements-dev.txt
docker compose up -d db
pytest
```

Тесты используют отдельную базу `zhibek_test` (создаётся сама), схему накатывают миграциями и перед каждым тестом чистят таблицы.

## Структура

```
app/
  main.py         сборка приложения: роутеры, обработчики ошибок, статика, seed при старте
  db.py           engine, SessionLocal, Base и зависимость get_db
  models.py       модели SQLAlchemy (таблицы и связи)
  storage.py      пути к файлам в static/
  seed.py         15 товаров с фотографиями и 4 образа (если база пустая)
  security.py     хеширование паролей (bcrypt) и создание/проверка JWT
  dependencies.py get_current_user, require_admin, ensure_owner_or_admin
  exceptions.py   свои исключения (400, 401, 403, 404, 409, 415, 429, 502) и обработчики
  llm.py          один запрос к Gemini через httpx
  schemas/        Pydantic-модели запросов и ответов
  services/       вся бизнес-логика (обычные функции)
  routers/        тонкие роутеры: принять → вызвать сервис → вернуть
alembic/          миграции схемы
tests/            тесты API на отдельной базе
static/
  *.html, style.css, app.js   фронт
  catalog/                    фотографии товаров
  uploads/, results/          фото пользователей и результаты примерок
```

## Эндпоинты

Доступ: **все** — без токена; **владелец** — только сам пользователь (`{id}` в пути или владелец заказа/примерки) или админ;
**админ** — только `role = admin`. Без токена → 401, чужой ресурс или нет прав → 403.

| Метод | Путь | Что делает | Доступ | Коды |
|---|---|---|---|---|
| POST | `/auth/register` | Регистрация `{email, password, ...анкета}` | все | 201, 409, 422 |
| POST | `/auth/login` | Вход `{email, password}` → `{access_token, token_type}` | все | 200, 401, 422 |
| GET | `/auth/me` | Текущий пользователь по токену | с токеном | 200, 401 |
| GET | `/items` | Список товаров, фильтры `category`, `color`, `min_price`, `max_price`, `in_stock` | все | 200, 422 |
| GET | `/items/{id}` | Один товар | все | 200, 404 |
| POST | `/items` | Создать товар | админ | 201, 401, 403, 404, 422 |
| PATCH | `/items/{id}` | Изменить товар (только переданные поля) | админ | 200, 401, 403, 404, 422 |
| DELETE | `/items/{id}` | Удалить товар | админ | 204, 401, 403, 404, 409 |
| GET | `/items/{id}/matches?limit=4` | «Дополни образ» — рекомендации по правилам | все | 200, 404, 422 |
| GET | `/looks` | Список образов | все | 200 |
| GET | `/looks/{id}` | Образ вместе с товарами | все | 200, 404 |
| GET | `/users` | Список анкет | админ | 200, 401, 403 |
| GET | `/users/{id}` | Одна анкета | владелец | 200, 401, 403, 404 |
| PATCH | `/users/{id}` | Изменить анкету | владелец | 200, 401, 403, 404, 422 |
| DELETE | `/users/{id}` | Удалить анкету вместе с фото, примерочной и примерками | владелец | 204, 401, 403, 404, 409 |
| POST | `/users/{id}/photo` | Загрузить фото пользователя (файл, JPEG или PNG до 5 МБ) | владелец | 200, 400, 401, 403, 404, 415 |
| GET | `/users/{id}/fitting-room` | Примерочная с суммой | владелец | 200, 401, 403, 404 |
| POST | `/users/{id}/fitting-room/items` | Добавить товар `{item_id, quantity}` | владелец | 201, 400, 401, 403, 404, 422 |
| PATCH | `/users/{id}/fitting-room/items/{item_id}` | Изменить количество `{quantity}` | владелец | 200, 400, 401, 403, 404, 422 |
| DELETE | `/users/{id}/fitting-room/items/{item_id}` | Убрать товар | владелец | 204, 401, 403, 404 |
| POST | `/users/{id}/orders` | Оформить заказ из примерочной | владелец | 201, 400, 401, 403, 404, 409 |
| GET | `/users/{id}/orders` | Заказы пользователя | владелец | 200, 401, 403, 404 |
| GET | `/orders/{id}` | Один заказ | владелец | 200, 401, 403, 404 |
| PATCH | `/orders/{id}/status` | Сменить статус `{status}`: владелец — `paid`/`cancelled`, `shipped` — только админ | владелец / админ | 200, 401, 403, 404, 409, 422 |
| POST | `/users/{id}/try-ons` | AI-примерка `{item_ids}` (1–3 вещи) | владелец | 201, 400, 401, 403, 404, 422, 429, 502 |
| GET | `/users/{id}/try-ons` | История примерок пользователя | владелец | 200, 401, 403, 404 |
| GET | `/try-ons/{id}` | Одна примерка | владелец | 200, 401, 403, 404 |
| DELETE | `/try-ons/{id}` | Удалить примерку и файл результата | владелец | 204, 401, 403, 404 |

Любая ошибка возвращается в одном формате:

```json
{"error": "not_found", "detail": "Item 42 not found"}
```

| Код | `error` | Когда |
|---|---|---|
| 400 | `business_rule` | нарушено бизнес-правило (нет столько на складе, примерочная пуста, нет фото для примерки) |
| 401 | `unauthorized` | нет токена, токен подделан или просрочен, неверный email или пароль при входе |
| 403 | `forbidden` | токен верный, но действие запрещено: чужой ресурс или нужна роль админа |
| 404 | `not_found` | объекта с таким id нет |
| 409 | `conflict` | действие противоречит текущему состоянию (товар в примерочной, недопустимый статус) |
| 415 | `unsupported_media_type` | загружен файл не JPEG и не PNG |
| 422 | `validation_error` | Pydantic не принял входные данные |
| 429 | `too_many_requests` | исчерпан дневной лимит примерок |
| 502 | `bad_gateway` | Gemini недоступна или не вернула картинку |

## Регистрация, вход и права

1. `POST /auth/register` — Pydantic проверяет email и пароль (8–72 символа), занятый email → 409.
   Пароль сохраняется только как bcrypt-хеш. Роль всегда `user`.
2. `POST /auth/login` — проверяем email и пароль, на любую ошибку один ответ 401 `Invalid email or password`.
   В ответ JWT: `{"sub": "<id>", "exp": <через 60 минут>}`, подписан `SECRET_KEY` (HS256).
3. Дальше клиент шлёт заголовок `Authorization: Bearer <token>`. Зависимость `get_current_user`
   проверяет подпись и срок и достаёт пользователя из базы. Иначе 401.
4. Права: `require_admin` — для каталога и списка пользователей; `ensure_owner_or_admin` — для личных данных.
   Иначе 403.

В Swagger: вызвать `/auth/login`, скопировать `access_token`, нажать **Authorize** и вставить токен.
Выход — фронт просто удаляет токен (JWT нигде на сервере не хранится).

## Четыре workflow

### 1. Каталог и «дополни образ» — `services/items.py`

- CRUD товаров и фильтрация списка.
- Товар нельзя удалить, пока он лежит в чьей-то примерочной → 409.
- Состав образа (`item_ids`) считается по полю `look_id` у товаров, чтобы связь хранилась в одном месте.
- `GET /items/{id}/matches` — рекомендации без ML:
  1. берём товары из сочетающихся категорий (словарь `MATCHING_CATEGORIES`: верх → низ, обувь, сумка, верхняя одежда и т. д.);
  2. оставляем сочетающиеся цвета: одинаковый цвет или один из двух нейтральный (белый, чёрный, серый, бежевый);
  3. убираем сам товар и товары с `stock = 0`;
  4. вещи из того же образа ставим первыми и берём сначала по одной вещи каждой категории.

### 2. Профиль пользователя — `services/users.py`

- CRUD анкеты: имя, рост (100–250), вес (30–250), пол, тип фигуры, любимый стиль.
- Пользователя нельзя удалить, пока у него есть заказ в статусе `pending` или `paid` → 409. Иначе он удаляется
  вместе с фото, примерочной и примерками.

### 3. Примерочная → заказ — `services/fitting_room.py`, `services/orders.py`

- Примерочная — это корзина, одна на пользователя: строки таблицы `fitting_room_rows` `{item_id, quantity}`.
- Правила добавления: товар существует (404); количество не больше остатка (400); не больше 10 позиций (400);
  повторное добавление того же товара увеличивает количество, а не создаёт дубль.
- Оформление заказа: пустая примерочная → 400; повторная проверка остатков → 409 (остаток мог измениться);
  затем остатки списываются, в заказ пишется снапшот товаров (название, цена, количество), считается `total`, примерочная очищается.
- Статусы: `pending → paid → shipped`, из `pending` и `paid` можно в `cancelled`. Любой другой переход → 409.
  При отмене товары возвращаются на склад.

### 4. AI-примерка — `services/try_on.py`, `llm.py`

Gemini получает фото пользователя и фото выбранных вещей и возвращает картинку, где человек одет в эти вещи.

- Фото пользователя: `POST /users/{id}/photo`. Формат проверяется по первым байтам файла: не JPEG и не PNG → 415,
  больше 5 МБ → 400. Файл сохраняется в `static/uploads/`, путь пишется в поле `photo_url` анкеты.
- Примерка: `POST /users/{id}/try-ons` с `item_ids` (от 1 до 3, иначе 422). Проверки по порядку:
  1. у пользователя нет фото → 400;
  2. какого-то товара нет → 404;
  3. больше одной вещи на категорию → 400;
  4. у вещи нет фотографии в `static/` → 400;
  5. уже было 3 примерки за последние 24 часа → 429. Считаются все попытки, дошедшие до генерации, включая неудачные;
     удаление примерки из истории лимит не сбрасывает (удаление мягкое, строка в `try_ons` остаётся).
- Сервис собирает промпт (рост, вес, тип фигуры + «одень человека с первого фото в вещи с остальных фото, сохрани лицо, позу и фон»)
  и кодирует фото в base64. `llm.generate_try_on` делает один POST в Gemini (таймаут 90 с) и достаёт из ответа первую часть с `inlineData`.
- Результат сохраняется в `static/results/{id}.png`, запись получает `status: done` и `result_url`.
- Если ключа нет, Gemini ответила ошибкой, случился таймаут или в ответе нет картинки — `llm.py` бросает `LLMError`.
  Сервер не падает: примерка остаётся в истории со `status: failed` и текстом ошибки, клиент получает 502 в общем формате.
- `LLM_MOCK=true`: Gemini не вызывается, `result_url` — копия фото пользователя, `source: "mock"`.

## Проверки в Swagger

Откройте `/docs` на чистой базе (`docker compose down -v && docker compose up -d --build`) и идите сверху вниз. Прочерк значит, что в этом workflow такого правила нет.

Перед проверками зарегистрируйтесь, войдите через `/auth/login` и вставьте токен в **Authorize**. Для `POST/PATCH/DELETE /items`
и `shipped` нужен админ: задайте `ADMIN_EMAIL` и `ADMIN_PASSWORD` в `.env` и войдите под ним.

### Workflow 1. Каталог

| Проверка | Запрос | Ожидаем |
|---|---|---|
| Успех | `GET /items?category=top&in_stock=true` | 200, только верх в наличии |
| Успех | `GET /items/1/matches` | 200, брюки, жилет, туфли и сумка |
| Успех | `POST /items` `{"name":"Шарф","category":"accessory","color":"серый","price":5000,"stock":2}` | 201, `id: 16` |
| 422 | `POST /items` с `"price": -5` или `"category": "hat"` | 422 `validation_error` |
| 404 | `GET /items/999` | 404 `not_found` |
| 409 | `DELETE /items/1` после шага «Успех» из workflow 3 (товар лежит в примерочной) | 409 `conflict` |
| 400 | — | |

### Workflow 2. Профиль

| Проверка | Запрос | Ожидаем |
|---|---|---|
| Успех | `POST /auth/register` `{"email":"aigerim@example.com","password":"secret123","name":"Айгерим","height_cm":168,"weight_kg":58,"gender":"female","body_type":"slim"}` | 201, `role: user`, `photo_url: null` |
| Успех | `PATCH /users/1` `{"weight_kg": 59}` | 200, остальные поля не изменились |
| 422 | `POST /auth/register` с `"height_cm": 50` или `"password": "123"` | 422 `validation_error` |
| 409 | повторный `POST /auth/register` с тем же email | 409 `conflict` |
| 401 | `POST /auth/login` с неверным паролем; любой запрос владельца без токена | 401 `unauthorized` |
| 403 | `GET /users/2` с токеном пользователя 1; `POST /items` с токеном не-админа | 403 `forbidden` |
| 404 | `GET /users/999` | 404 `not_found` |
| 409 | `DELETE /users/1`, пока у пользователя есть заказ `pending` (после workflow 3) | 409 `conflict` |
| 400 | — | |

### Workflow 3. Примерочная → заказ

| Проверка | Запрос | Ожидаем |
|---|---|---|
| 400 | `POST /users/1/orders` при пустой примерочной | 400 `business_rule` |
| Успех | `POST /users/1/fitting-room/items` `{"item_id":1,"quantity":2}` | 201, в примерочной одна позиция |
| Успех | тот же запрос с `"quantity": 1` | 201, позиция одна, `quantity: 3` |
| 400 | `POST /users/1/fitting-room/items` `{"item_id":11,"quantity":4}` (на складе 3) | 400 `business_rule` |
| 422 | `POST /users/1/fitting-room/items` `{"item_id":1,"quantity":0}` | 422 `validation_error` |
| 404 | `POST /users/1/fitting-room/items` `{"item_id":999,"quantity":1}` | 404 `not_found` |
| 409 | `PATCH /items/1` `{"stock":1}`, затем `POST /users/1/orders` | 409 `conflict` — остатка уже не хватает |
| Успех | `PATCH /items/1` `{"stock":12}`, затем `POST /users/1/orders` | 201, `status: pending`, `total: 65700`; остаток товара 1 стал 9, примерочная пуста |
| 409 | `PATCH /orders/1/status` `{"status":"shipped"}` | 409 — из `pending` нельзя сразу в `shipped` |
| Успех | `PATCH /orders/1/status` `{"status":"paid"}`, затем `{"status":"cancelled"}` | 200; после отмены остаток товара 1 снова 12 |
| 400 | добавить в примерочную товары 1–10, затем товар 11 | 400 — максимум 10 позиций |

### Workflow 4. AI-примерка

Шаги до «502» удобно проходить с `LLM_MOCK=true` в `.env`.

| Проверка | Запрос | Ожидаем |
|---|---|---|
| 400 | `POST /users/1/try-ons` `{"item_ids":[1]}` до загрузки фото | 400 `business_rule` |
| 415 | `POST /users/1/photo` с файлом `.txt` или `.pdf` | 415 `unsupported_media_type` |
| 400 | `POST /users/1/photo` с JPEG больше 5 МБ | 400 `business_rule` |
| Успех | `POST /users/1/photo` с обычным JPEG или PNG | 200, в анкете появился `photo_url` |
| 422 | `POST /users/1/try-ons` `{"item_ids":[]}` или четыре id | 422 `validation_error` |
| 404 | `POST /users/1/try-ons` `{"item_ids":[1,999]}` | 404 `not_found` |
| 400 | `POST /users/1/try-ons` `{"item_ids":[1,5]}` (два верха) | 400 `business_rule` |
| Успех | `POST /users/1/try-ons` `{"item_ids":[1,2,4]}` | 201, `status: done`, `source: "mock"` (или `"gemini"` с ключом), картинка открывается по `result_url` |
| Успех | `GET /users/1/try-ons`, `GET /try-ons/1` | 200 |
| Успех | `DELETE /try-ons/1` | 204, файл по `result_url` больше не открывается |
| 429 | ещё две примерки, затем четвёртая за сутки | 429 `too_many_requests` (удаление примерки лимит не вернуло) |
| 502 | убрать `LLM_MOCK` и ключ из `.env`, перезапустить, загрузить фото, `POST /users/1/try-ons` | 502 `bad_gateway`, сервер жив; в `GET /users/1/try-ons` запись со `status: failed` и текстом ошибки |
| 409 | — | |

### Сохранность данных

| Проверка | Запрос | Ожидаем |
|---|---|---|
| Успех | создать пользователя и заказ, затем `docker compose restart app` | `GET /users/1`, `GET /users/1/orders` возвращают те же данные |
| Успех | `PATCH /items/1` `{"look_id": null}` | 200, товар убран из образа, `GET /looks/1` больше его не содержит |
| 400 | `PATCH /items/1` `{"name": null}` | 400 `business_rule` — обязательное поле нельзя обнулить |
