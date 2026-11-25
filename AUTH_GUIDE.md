# AUTH GUIDE — шпаргалка по авторизации (Assignment 7)

Только то, что сделано в этом задании: регистрация, вход по JWT, права доступа, тесты.

---

## 0. Одной фразой

Пароль хранится как **bcrypt-хеш** в PostgreSQL. После входа сервер выдаёт **JWT-токен**. Клиент шлёт его в заголовке
`Authorization: Bearer <token>`. Зависимость **`get_current_user`** узнаёт пользователя, **`require_admin`** и
**`ensure_owner_or_admin`** решают, можно ли ему.

| Слово | Вопрос | Ошибка |
|---|---|---|
| Аутентификация | «кто ты?» | **401** |
| Авторизация | «что тебе можно?» | **403** |

---

## 1. Карта файлов

```
app/
├── security.py         пароли (bcrypt) + токены (JWT)                 ← НОВЫЙ
├── dependencies.py     охранники: кто ты / админ ли / твоё ли          ← НОВЫЙ
├── schemas/auth.py     RegisterIn, LoginIn, TokenOut                   ← НОВЫЙ
├── services/auth.py    register(), login()                             ← НОВЫЙ
├── routers/auth.py     /auth/register, /auth/login, /auth/me           ← НОВЫЙ
├── models.py           User: + email, password_hash, role
├── schemas/users.py    + Role (user/admin), UserOut: + email, role
├── exceptions.py       + UnauthorizedError (401), ForbiddenError (403)
├── seed.py             + create_admin() из ADMIN_EMAIL / ADMIN_PASSWORD
├── main.py             подключён роутер auth, вызов create_admin()
└── routers/*.py        в эндпоинты добавлены охранники
alembic/versions/a1c4e7f2b9d0_auth_for_users.py   миграция              ← НОВЫЙ
tests/test_auth.py      20 тестов                                       ← НОВЫЙ
tests/conftest.py       + фикстуры user, other_user, admin
static/app.js, profile.html   вход, регистрация, выход, токен в запросах
```

Слои: **router** (URL) → **service** (логика) → **security** (крипта). Роутер сам ничего не считает.

---

## 2. Функции: что делает каждая

### `app/security.py`
| Функция | Делает |
|---|---|
| `hash_password(p)` | пароль → `$2b$12$...` (bcrypt, случайная соль) |
| `verify_password(p, h)` | подходит ли пароль к хешу → True/False; >72 байт → False |
| `create_access_token(id)` | JWT `{"sub": "5", "exp": +60 мин}`, подпись HS256 ключом `SECRET_KEY` |
| `decode_access_token(t)` | проверяет подпись, срок, наличие `exp`/`sub` → id или `None` |
| `DUMMY_HASH` | хеш-пустышка: вход с чужим email идёт столько же, сколько с настоящим |

### `app/dependencies.py`
| Функция | Делает | Ошибка |
|---|---|---|
| `bearer` (`HTTPBearer`) | достаёт токен из `Authorization: Bearer ...`, даёт кнопку Authorize в Swagger | — |
| `get_current_user` | токен есть? → подпись/срок ок? → пользователь есть в базе? → `User` | 401 |
| `require_admin` | `role == admin`? | 403 |
| `ensure_owner_or_admin(owner_id, user)` | хозяин или админ? (вызывается вручную в эндпоинте) | 403 |

### `app/services/auth.py`
| Функция | Делает |
|---|---|
| `find_by_email` | `SELECT * FROM users WHERE email = ...` (email в нижнем регистре) |
| `register` | email занят → 409; иначе `hash_password` → `INSERT` (роль всегда `user`) |
| `login` | найти по email → `verify_password` → неверно 401 / верно токен |

### `app/schemas/auth.py`
| Класс | Проверки |
|---|---|
| `RegisterIn` | анкета + `EmailStr` + пароль ≥ 8 символов и ≤ 72 **байт** |
| `LoginIn` | email + пароль |
| `TokenOut` | `{"access_token", "token_type": "bearer"}` |

---

## 3. Три потока

```
РЕГИСТРАЦИЯ   POST /auth/register
  RegisterIn (422) → find_by_email (409) → hash_password → INSERT users → 201

ВХОД          POST /auth/login
  find_by_email → verify_password (401) → create_access_token → {access_token}
  фронт кладёт токен в localStorage (app.js → login())

ЗАПРОС        GET /users/5/orders + Authorization: Bearer eyJ...
  bearer (нет → 401) → get_current_user (плохой → 401)
  → ensure_owner_or_admin (чужое → 403) → сервис → ответ

ВЫХОД         фронт удаляет токен (app.js → clearSession()). На сервере токен не хранится.
```

---

## 4. Кто что может

| Действие | Гость | User | Admin |
|---|---|---|---|
| Смотреть товары, образы | ✅ | ✅ | ✅ |
| Создать / изменить / удалить товар | 401 | 403 | ✅ |
| Список всех пользователей | 401 | 403 | ✅ |
| Свой профиль, фото, примерочная, заказы, примерки | 401 | ✅ | ✅ |
| Чужие | 401 | 403 | ✅ |
| Заказ → `paid` / `cancelled` | 401 | ✅ свой | ✅ |
| Заказ → `shipped` | 401 | 403 | ✅ |

- Админом нельзя стать через регистрацию: `role` из запроса игнорируется.
- Админ создаётся при старте из `.env`: `ADMIN_EMAIL`, `ADMIN_PASSWORD` (в Docker по умолчанию `admin@zhibek.kz` / `adminpass123`).
- `POST /users` удалён: вместо него `POST /auth/register`.

---

## 5. Библиотеки

| Библиотека | Зачем | Где |
|---|---|---|
| `bcrypt` | хеш паролей | `security.py` |
| `PyJWT` (`import jwt`) | создать и проверить токен | `security.py` |
| `email-validator` | работа `EmailStr` в Pydantic | `schemas/auth.py` |
| `fastapi.security.HTTPBearer` | прочитать заголовок `Authorization` | `dependencies.py` |

**Шифрования в проекте нет.** Есть хеширование (необратимо) и подпись (содержимое открыто, подделать нельзя).

---

## 6. bcrypt за 30 секунд

- `$2b$` `12` `$` **соль (22)** **хеш (31)**: всё в одной строке в `users.password_hash`.
- **Соль** случайная, поэтому одинаковые пароли дают разные хеши и готовые таблицы (rainbow tables) не работают.
- **Проверка:** взять соль из сохранённого хеша → захешировать введённый пароль → сравнить.
- **Медленный специально:** ~0.2 с на проверку (sha256 примерно в 800 000 раз быстрее). Пользователь не заметит, перебор для хакера дорогой.
- **Предел 72 байта:** кириллица — 2 байта на букву, поэтому считаем байты, а не символы.

## 7. JWT за 30 секунд

- `header.payload.signature`, каждая часть в base64.
- payload `{"sub": "5", "exp": ...}` **читается без ключа**, поэтому паролей в токене нет.
- signature = HMAC-SHA256(`SECRET_KEY`, header.payload). Поменяешь `sub`, и подпись не сойдётся → 401.
- `algorithms=["HS256"]` закрывает атаку `alg: none`; `require: ["exp", "sub"]` значит, что вечных токенов нет.
- `SECRET_KEY` лежит в `.env` (не в git). Украдут ключ, и можно подделать любой токен, поэтому ключ нужно сменить.
- Роль в токен не кладём: она читается из базы на каждый запрос, поэтому изменения роли срабатывают сразу.

---

## 8. База и миграция

- PostgreSQL, база `zhibek`, таблица `users`, новые колонки:
  `email` (UNIQUE `uq_users_email`), `password_hash`, `role` (enum `user_role`, по умолчанию `user`).
- Миграция `a1c4e7f2b9d0`: `upgrade()` удаляет старых пользователей без пароля (их данные уходят по CASCADE)
  и добавляет колонки; `downgrade()` откатывает всё обратно.
- `alembic upgrade head` в Docker выполняется сам при старте.
- Токен в базе **не хранится**.

---

## 9. Ключевые понятия FastAPI

- **`Depends(f)`**: «перед эндпоинтом вызови `f` и дай результат». Зависимости цепочкой:
  `require_admin → get_current_user → bearer + get_db`. Одна зависимость вызывается один раз за запрос.
- **`get_db` с `yield`**: до `yield` открыть сессию, отдать эндпоинту, после ответа `finally: close()`.
  С `return` закрыть после работы эндпоинта было бы нельзя.
- **`HTTPBearer(auto_error=False)`**: без заголовка не падаем сами, а отвечаем 401 в общем формате ошибок.
- Ответ 401 содержит заголовок `WWW-Authenticate: Bearer` (требование HTTP).

---

## 10. Тесты

`tests/test_auth.py`, 20 тестов. Схема каждого: **запрос → ответ → `assert` кода и данных**.

| Группа | Что проверяем |
|---|---|
| Регистрация | 201, хеш в базе (не пароль), дубль 409, плохие данные 422, нельзя стать админом |
| Вход | токен выдаётся; неверный пароль и чужой email — одинаковый 401 |
| Токены | без токена 401; мусор, просрочка, чужая подпись, без `exp` 401; удалённый пользователь 401 |
| Чужое | профиль, примерочная, заказы, примерки другого → 403, данные не изменились |
| Роли | товары: гость 401 / user 403 / admin 201; список пользователей только админу; `shipped` только админу |
| Осмотр | кириллический пароль работает; >72 байт → 422, а не 500 |

Фикстуры (`conftest.py`): `client` (чистая база `zhibek_test` перед каждым тестом), `user`, `other_user`, `admin`.

```bash
source .venv/bin/activate
docker compose up -d db
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/test_auth.py -v          # 20 passed
pytest                                # все 29
```

---

## 11. Демо на защите

1. `docker compose up -d --build` → http://127.0.0.1:8090/docs
2. `POST /auth/register` → 201. Повторить с тем же email → 409.
3. `POST /auth/login` → скопировать `access_token` → **Authorize** → вставить.
4. `GET /auth/me` → твой пользователь. Без токена → 401.
5. `GET /users/<чужой id>` → 403. `POST /items` под обычным пользователем → 403.
6. Войти админом (`admin@zhibek.kz` / `adminpass123`) → `POST /items` → 201.
7. Тесты ловят дыры: закомментировать `if` в `ensure_owner_or_admin` → `pytest tests/test_auth.py` красный → вернуть.

---

## 12. Слабые места (назвать самому)

| Что | Как закрыть |
|---|---|
| Нет HTTPS локально, токен идёт открытым текстом | HTTPS на сервере (nginx или хостинг) |
| Нет лимита попыток входа | rate limit на `/auth/login` |
| Токен в `localStorage` можно украсть через XSS | `httpOnly`-cookie |
| Logout не убивает токен на сервере | короткий `exp`, refresh-токены, чёрный список |
| Фото `/uploads/user_<id>.png` открыты без токена | отдавать файлы через защищённый эндпоинт |
| Пароль админа и `SECRET_KEY` по умолчанию видны в compose | задать свои в `.env` |

---

## 13. Быстрые ответы

- **Хеш vs шифрование?** Хеш необратим, шифрование расшифровывается ключом.
- **Зачем соль, если она открыта?** Чтобы одинаковые пароли давали разные хеши.
- **JWT зашифрован?** Нет, подписан: читать можно, подделать нельзя.
- **Где хранится токен?** У клиента (`localStorage`). Сервер его не хранит, он stateless.
- **401 vs 403?** «Не знаю, кто ты» против «знаю, но нельзя».
- **Почему 403, а не 404 на чужое?** Проще объяснить. 404 скрыл бы сам факт, что ресурс есть, но учебному проекту это не нужно.
- **Почему одна ошибка на неверный email и пароль?** Чтобы нельзя было узнать, какие email зарегистрированы.
- **Почему `UNIQUE` в базе, если email уже проверяется в коде?** Два одновременных запроса оба пройдут проверку в коде, а база второй не пропустит.
- **Почему роль не в токене?** Роль читается из базы на каждый запрос, поэтому разжалованный админ теряет права сразу.
