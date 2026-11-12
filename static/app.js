// Общий скрипт для всех страниц. Какая страница открыта, видно по <body data-page="...">.

const CATEGORY_NAMES = {
  top: "Верх",
  bottom: "Низ",
  outerwear: "Верхняя одежда",
  shoes: "Обувь",
  bag: "Сумки",
  accessory: "Аксессуары",
};

const STATUS_NAMES = {
  pending: "Ожидает оплаты",
  paid: "Оплачен",
  shipped: "Отправлен",
  cancelled: "Отменён",
};

// цвет товара -> цвет блока-плейсхолдера
const COLOR_HEX = {
  "белый": "#fffdf8",
  "чёрный": "#2a211c",
  "серый": "#a39d95",
  "бежевый": "#dcc9a8",
  "терракотовый": "#a9482d",
  "синий": "#3d5470",
  "оливковый": "#74774d",
  "коричневый": "#6e4a35",
};

// ---------- помощники ----------

// Запрос к API. При ошибке бросает Error с текстом из поля detail.
async function api(method, path, body) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.detail || "Ошибка запроса");
    error.status = response.status;
    throw error;
  }
  return data;
}

function getUserId() {
  return localStorage.getItem("user_id");
}

function money(amount) {
  return amount.toLocaleString("ru-RU") + " ₸";
}

function escapeHtml(text) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return String(text).replace(/[&<>"']/g, (char) => map[char]);
}

function setMessage(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle("error", isError);
}

function showToast(text, isError = false) {
  const toast = document.getElementById("toast");
  setMessage(toast, text, isError);
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => (toast.hidden = true), 3000);
}

// Картинка товара: фото из image_url или цветной блок с названием категории
function thumb(item) {
  if (item.image_url) {
    return `<div class="thumb"><img src="${escapeHtml(item.image_url)}" alt=""></div>`;
  }
  const hex = COLOR_HEX[item.color.toLowerCase()] || "#ede3d4";
  const isDark = parseInt(hex.slice(1, 3), 16) + parseInt(hex.slice(3, 5), 16) + parseInt(hex.slice(5, 7), 16) < 400;
  const textColor = isDark ? "#f7f1e7" : "#2a211c";
  return `<div class="thumb" style="background:${hex};color:${textColor}">${CATEGORY_NAMES[item.category]}</div>`;
}

function itemCard(item) {
  const stock = item.stock > 0 ? `в наличии ${item.stock}` : "нет в наличии";
  return `
    <article class="card" tabindex="0" data-id="${item.id}" data-name="${escapeHtml(item.name)}">
      ${thumb(item)}
      <h3>${escapeHtml(item.name)}</h3>
      <p class="meta">${escapeHtml(item.color)} · ${stock}</p>
      <div class="card-row">
        <span class="price">${money(item.price)}</span>
        <button class="btn small" type="button" data-add="${item.id}" ${item.stock > 0 ? "" : "disabled"}>В примерочную</button>
      </div>
    </article>`;
}

// Счётчик позиций примерочной в шапке
async function updateRoomCount() {
  const badge = document.getElementById("room-count");
  badge.hidden = true;
  if (!getUserId()) return;
  try {
    const room = await api("GET", `/users/${getUserId()}/fitting-room`);
    badge.textContent = room.items.length;
    badge.hidden = room.items.length === 0;
  } catch (error) {
    // данные в памяти: после перезапуска сервера пользователя из localStorage уже нет
    if (error.status === 404) localStorage.removeItem("user_id");
  }
}

async function addToRoom(itemId) {
  if (!getUserId()) {
    showToast("Сначала заполните анкету в профиле", true);
    return;
  }
  try {
    await api("POST", `/users/${getUserId()}/fitting-room/items`, { item_id: itemId, quantity: 1 });
    showToast("Добавлено в примерочную");
    updateRoomCount();
  } catch (error) {
    showToast(error.message, true);
  }
}

// Клики по карточкам товаров (каталог и результат стилиста)
document.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-add]");
  const card = event.target.closest(".card[data-id]");
  if (addButton) {
    addToRoom(Number(addButton.dataset.add));
  } else if (card && document.getElementById("matches")) {
    showMatches(card.dataset.id, card.dataset.name);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.matches(".card[data-id]")) event.target.click();
});

// ---------- главная ----------

function lookCard(look) {
  const total = look.items.reduce((sum, item) => sum + item.price, 0);
  return `
    <a class="card" href="catalog.html?look=${look.id}">
      <div class="mosaic">${look.items.slice(0, 4).map(thumb).join("")}</div>
      <h3>${escapeHtml(look.title)}</h3>
      <p class="meta">Вещей: ${look.items.length} · ${money(total)}</p>
    </a>`;
}

async function initHome() {
  try {
    const looks = await api("GET", "/looks");
    const details = await Promise.all(looks.map((look) => api("GET", `/looks/${look.id}`)));
    document.getElementById("looks").innerHTML = details.map(lookCard).join("");
  } catch (error) {
    document.getElementById("looks-error").textContent = error.message;
  }
}

// ---------- каталог ----------

async function initCatalog() {
  const params = new URLSearchParams(location.search);
  const category = params.get("category") || "";
  const lookId = params.get("look");

  // фильтр — обычные ссылки: catalog.html?category=top
  const chips = [["", "Все"], ...Object.entries(CATEGORY_NAMES)];
  document.getElementById("filters").innerHTML = chips
    .map(([value, title]) => {
      const active = !lookId && value === category ? "active" : "";
      const href = value ? `catalog.html?category=${value}` : "catalog.html";
      return `<a class="chip ${active}" href="${href}">${title}</a>`;
    })
    .join("");

  try {
    let items;
    if (lookId) {
      const look = await api("GET", `/looks/${encodeURIComponent(lookId)}`);
      document.getElementById("catalog-title").textContent = `Образ «${look.title}»`;
      items = look.items;
    } else {
      items = await api("GET", category ? `/items?category=${encodeURIComponent(category)}` : "/items");
    }
    document.getElementById("items").innerHTML =
      items.map(itemCard).join("") || '<p class="muted">Ничего не найдено.</p>';
  } catch (error) {
    document.getElementById("catalog-error").textContent = error.message;
  }

  document.getElementById("matches-close").addEventListener("click", () => {
    document.getElementById("matches").hidden = true;
  });
}

// Блок «дополните образ» для выбранной вещи
async function showMatches(itemId, itemName) {
  const block = document.getElementById("matches");
  try {
    const matches = await api("GET", `/items/${itemId}/matches?limit=4`);
    document.getElementById("matches-title").textContent = `Дополните образ: ${itemName}`;
    document.getElementById("matches-list").innerHTML =
      matches.map(itemCard).join("") || '<p class="muted">Подходящих вещей в наличии нет.</p>';
    block.hidden = false;
    block.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    showToast(error.message, true);
  }
}

// ---------- профиль и стилист ----------

async function initProfile() {
  const form = document.getElementById("profile-form");
  const message = document.getElementById("profile-message");
  const deleteButton = document.getElementById("profile-delete");

  if (getUserId()) {
    try {
      const user = await api("GET", `/users/${getUserId()}`);
      for (const [key, value] of Object.entries(user)) {
        if (form.elements[key]) form.elements[key].value = value ?? "";
      }
      deleteButton.hidden = false;
    } catch (error) {
      setMessage(message, error.message, true);
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = {
      name: form.elements.name.value.trim(),
      height_cm: Number(form.elements.height_cm.value),
      weight_kg: Number(form.elements.weight_kg.value),
      gender: form.elements.gender.value,
      body_type: form.elements.body_type.value,
      style_preference: form.elements.style_preference.value.trim(),
    };
    try {
      // анкета уже есть — обновляем, иначе создаём
      const user = getUserId()
        ? await api("PATCH", `/users/${getUserId()}`, data)
        : await api("POST", "/users", data);
      localStorage.setItem("user_id", user.id);
      deleteButton.hidden = false;
      setMessage(message, "Анкета сохранена");
    } catch (error) {
      setMessage(message, error.message, true);
    }
  });

  deleteButton.addEventListener("click", async () => {
    if (!confirm("Удалить анкету вместе с примерочной?")) return;
    try {
      await api("DELETE", `/users/${getUserId()}`);
      localStorage.removeItem("user_id");
      form.reset();
      deleteButton.hidden = true;
      setMessage(message, "Анкета удалена");
      updateRoomCount();
    } catch (error) {
      setMessage(message, error.message, true);
    }
  });

  const stylistForm = document.getElementById("stylist-form");
  const stylistMessage = document.getElementById("stylist-message");
  const result = document.getElementById("stylist-result");

  stylistForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!getUserId()) {
      setMessage(stylistMessage, "Сначала сохраните анкету", true);
      return;
    }
    const data = { occasion: stylistForm.elements.occasion.value.trim() };
    if (stylistForm.elements.budget.value) data.budget = Number(stylistForm.elements.budget.value);

    const button = stylistForm.querySelector("button");
    button.disabled = true;
    setMessage(stylistMessage, "Стилист подбирает образ…");
    try {
      const outfit = await api("POST", `/users/${getUserId()}/stylist`, data);
      document.getElementById("stylist-comment").textContent = outfit.comment;
      document.getElementById("stylist-source").textContent =
        outfit.source === "llm" ? "Подобрал AI-стилист" : "Подбор по правилам";
      document.getElementById("stylist-items").innerHTML = outfit.items.map(itemCard).join("");
      document.getElementById("stylist-total").textContent = outfit.items.length ? `Итого: ${money(outfit.total)}` : "";
      result.hidden = false;
      setMessage(stylistMessage, "");
      result.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      setMessage(stylistMessage, error.message, true);
    }
    button.disabled = false;
  });
}

// ---------- примерочная и заказы ----------

function roomRow(row) {
  const id = row.item.id;
  return `
    <div class="row">
      ${thumb(row.item)}
      <div>
        <h3>${escapeHtml(row.item.name)}</h3>
        <p class="meta">${money(row.item.price)} · ${escapeHtml(row.item.color)}</p>
      </div>
      <div class="qty">
        <button type="button" data-item="${id}" data-qty="${row.quantity - 1}" aria-label="Меньше" ${row.quantity === 1 ? "disabled" : ""}>−</button>
        <span>${row.quantity}</span>
        <button type="button" data-item="${id}" data-qty="${row.quantity + 1}" aria-label="Больше">+</button>
      </div>
      <span class="price">${money(row.subtotal)}</span>
      <button class="link" type="button" data-remove="${id}">Убрать</button>
    </div>`;
}

function orderCard(order) {
  const date = new Date(order.created_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
  const lines = order.items
    .map((item) => `<li>${escapeHtml(item.name)} × ${item.quantity} — ${money(item.price * item.quantity)}</li>`)
    .join("");
  const button = (status, title, style = "") =>
    `<button class="btn small ${style}" type="button" data-order="${order.id}" data-status="${status}">${title}</button>`;

  // кнопки только для разрешённых переходов статуса
  let buttons = "";
  if (order.status === "pending") buttons = button("paid", "Оплатить") + button("cancelled", "Отменить", "ghost");
  if (order.status === "paid") buttons = button("shipped", "Отправить") + button("cancelled", "Отменить", "ghost");

  return `
    <div class="order">
      <div class="section-head">
        <h3>Заказ №${order.id} <span class="meta">от ${date}</span></h3>
        <span class="tag">${STATUS_NAMES[order.status]}</span>
      </div>
      <ul>${lines}</ul>
      <div class="actions">
        <span class="price">Итого: ${money(order.total)}</span>
        <span class="actions">${buttons}</span>
      </div>
    </div>`;
}

async function loadRoom() {
  const room = await api("GET", `/users/${getUserId()}/fitting-room`);
  document.getElementById("room-list").innerHTML =
    room.items.map(roomRow).join("") ||
    '<p class="muted">Пока пусто. Загляните в <a href="catalog.html">каталог</a>.</p>';
  document.getElementById("room-footer").hidden = room.items.length === 0;
  document.getElementById("room-total").textContent = `Итого: ${money(room.total)}`;
  updateRoomCount();
}

async function loadOrders() {
  const orders = await api("GET", `/users/${getUserId()}/orders`);
  document.getElementById("orders").innerHTML =
    orders.reverse().map(orderCard).join("") || '<p class="muted">Заказов пока нет.</p>';
}

async function initRoom() {
  const roomMessage = document.getElementById("room-message");
  const ordersMessage = document.getElementById("orders-message");

  if (!getUserId()) {
    roomMessage.innerHTML = 'Чтобы пользоваться примерочной, заполните <a href="profile.html">анкету</a>.';
    return;
  }

  // Выполнить действие и показать ошибку API под нужным блоком
  async function run(message, action) {
    try {
      setMessage(message, "");
      await action();
    } catch (error) {
      setMessage(message, error.message, true);
    }
  }

  document.getElementById("room-list").addEventListener("click", (event) => {
    const { item, qty, remove } = event.target.dataset;
    const base = `/users/${getUserId()}/fitting-room/items`;
    if (qty) {
      run(roomMessage, async () => {
        await api("PATCH", `${base}/${item}`, { quantity: Number(qty) });
        await loadRoom();
      });
    } else if (remove) {
      run(roomMessage, async () => {
        await api("DELETE", `${base}/${remove}`);
        await loadRoom();
      });
    }
  });

  document.getElementById("order-button").addEventListener("click", () => {
    run(roomMessage, async () => {
      const order = await api("POST", `/users/${getUserId()}/orders`);
      await loadRoom();
      await loadOrders();
      setMessage(roomMessage, `Заказ №${order.id} оформлен`);
    });
  });

  document.getElementById("orders").addEventListener("click", (event) => {
    const { order, status } = event.target.dataset;
    if (!order) return;
    run(ordersMessage, async () => {
      await api("PATCH", `/orders/${order}/status`, { status });
      await loadOrders();
    });
  });

  run(roomMessage, loadRoom);
  run(ordersMessage, loadOrders);
}

// ---------- запуск ----------

async function start() {
  await updateRoomCount(); // заодно забываем пользователя, которого уже нет на сервере
  const page = document.body.dataset.page;
  if (page === "home") initHome();
  if (page === "catalog") initCatalog();
  if (page === "profile") initProfile();
  if (page === "room") initRoom();
}

start();
