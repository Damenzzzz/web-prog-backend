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

async function api(method, path, body) {
  const options = { method };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
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

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
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

function thumb(item) {
  if (!item.image_url) return '<div class="thumb">Нет фото</div>';
  return `<div class="thumb"><img src="${escapeHtml(item.image_url)}" alt="" loading="lazy"></div>`;
}

function itemCard(item) {
  const stock = item.stock > 0 ? `в наличии ${item.stock}` : "нет в наличии";
  return `
    <article class="card" tabindex="0" data-id="${item.id}" data-name="${escapeHtml(item.name)}">
      ${thumb(item)}
      <h3>${escapeHtml(item.name)}</h3>
      <p class="meta">${CATEGORY_NAMES[item.category]} · ${escapeHtml(item.color)} · ${stock}</p>
      <div class="card-row">
        <span class="price">${money(item.price)}</span>
        <button class="btn small" type="button" data-add="${item.id}" ${item.stock > 0 ? "" : "disabled"}>В примерочную</button>
      </div>
    </article>`;
}

async function updateRoomCount() {
  const badge = document.getElementById("room-count");
  badge.hidden = true;
  if (!getUserId()) return;
  try {
    const room = await api("GET", `/users/${getUserId()}/fitting-room`);
    badge.textContent = room.items.length;
    badge.hidden = room.items.length === 0;
  } catch (error) {
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

async function initCatalog() {
  const params = new URLSearchParams(location.search);
  const category = params.get("category") || "";
  const lookId = params.get("look");

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

async function initProfile() {
  const form = document.getElementById("profile-form");
  const message = document.getElementById("profile-message");
  const deleteButton = document.getElementById("profile-delete");
  const photoForm = document.getElementById("photo-form");
  const photoMessage = document.getElementById("photo-message");
  const preview = document.getElementById("photo-preview");

  function showPhoto(url) {
    preview.src = url;
    preview.hidden = false;
  }

  if (getUserId()) {
    try {
      const user = await api("GET", `/users/${getUserId()}`);
      for (const [key, value] of Object.entries(user)) {
        if (form.elements[key]) form.elements[key].value = value ?? "";
      }
      if (user.photo_url) showPhoto(user.photo_url);
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
    if (!confirm("Удалить анкету вместе с фото, примерочной и примерками?")) return;
    try {
      await api("DELETE", `/users/${getUserId()}`);
      localStorage.removeItem("user_id");
      form.reset();
      photoForm.reset();
      preview.hidden = true;
      deleteButton.hidden = true;
      setMessage(message, "Анкета удалена");
      setMessage(photoMessage, "");
      updateRoomCount();
    } catch (error) {
      setMessage(message, error.message, true);
    }
  });

  photoForm.elements.file.addEventListener("change", () => {
    const file = photoForm.elements.file.files[0];
    if (file) showPhoto(URL.createObjectURL(file));
    setMessage(photoMessage, file ? "Фото выбрано, нажмите «Загрузить фото»" : "");
  });

  photoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!getUserId()) {
      setMessage(photoMessage, "Сначала сохраните анкету", true);
      return;
    }
    const data = new FormData();
    data.append("file", photoForm.elements.file.files[0]);
    try {
      const user = await api("POST", `/users/${getUserId()}/photo`, data);
      showPhoto(`${user.photo_url}?t=${Date.now()}`);
      setMessage(photoMessage, "Фото загружено");
    } catch (error) {
      setMessage(photoMessage, error.message, true);
    }
  });
}

const itemNames = {};

function roomRow(row) {
  const id = row.item.id;
  return `
    <div class="row">
      <input type="checkbox" data-try="${id}" aria-label="Выбрать для примерки: ${escapeHtml(row.item.name)}">
      ${thumb(row.item)}
      <div>
        <h3>${escapeHtml(row.item.name)}</h3>
        <p class="meta">${money(row.item.price)} · ${CATEGORY_NAMES[row.item.category]}</p>
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
  const lines = order.items
    .map((item) => `<li>${escapeHtml(item.name)} × ${item.quantity} — ${money(item.price * item.quantity)}</li>`)
    .join("");
  const button = (status, title, style = "") =>
    `<button class="btn small ${style}" type="button" data-order="${order.id}" data-status="${status}">${title}</button>`;

  let buttons = "";
  if (order.status === "pending") buttons = button("paid", "Оплатить") + button("cancelled", "Отменить", "ghost");
  if (order.status === "paid") buttons = button("shipped", "Отправить") + button("cancelled", "Отменить", "ghost");

  return `
    <div class="order">
      <div class="section-head">
        <h3>Заказ №${order.id} <span class="meta">от ${formatDate(order.created_at)}</span></h3>
        <span class="tag">${STATUS_NAMES[order.status]}</span>
      </div>
      <ul>${lines}</ul>
      <div class="actions">
        <span class="price">Итого: ${money(order.total)}</span>
        <span class="actions">${buttons}</span>
      </div>
    </div>`;
}

function tryOnCard(tryOn) {
  const names = tryOn.item_ids.map((id) => escapeHtml(itemNames[id] || `товар №${id}`)).join(", ");
  const result =
    tryOn.status === "done"
      ? `<div class="thumb"><img src="${escapeHtml(tryOn.result_url)}" alt="Результат примерки №${tryOn.id}" loading="lazy"></div>`
      : `<div class="thumb error">${escapeHtml(tryOn.error)}</div>`;
  return `
    <div class="card tryon-card">
      ${result}
      <h3>Примерка №${tryOn.id}</h3>
      <p class="meta">${formatDate(tryOn.created_at)} · ${names}</p>
      <div class="card-row">
        <span class="tag">${tryOn.source === "mock" ? "mock" : "Gemini"}</span>
        <button class="link" type="button" data-delete-try="${tryOn.id}">Удалить</button>
      </div>
    </div>`;
}

async function loadRoom() {
  const selector = "#room-list [data-try]";
  const checked = [...document.querySelectorAll(`${selector}:checked`)].map((box) => box.dataset.try);

  const room = await api("GET", `/users/${getUserId()}/fitting-room`);
  document.getElementById("room-list").innerHTML =
    room.items.map(roomRow).join("") ||
    '<p class="muted">Пока пусто. Загляните в <a href="catalog.html">каталог</a>.</p>';
  document.querySelectorAll(selector).forEach((box) => (box.checked = checked.includes(box.dataset.try)));

  document.getElementById("room-footer").hidden = room.items.length === 0;
  document.getElementById("tryon-block").hidden = room.items.length === 0;
  document.getElementById("room-total").textContent = `Итого: ${money(room.total)}`;
  updateRoomCount();
}

async function loadOrders() {
  const orders = await api("GET", `/users/${getUserId()}/orders`);
  document.getElementById("orders").innerHTML =
    orders.reverse().map(orderCard).join("") || '<p class="muted">Заказов пока нет.</p>';
}

async function loadTryOns() {
  const items = await api("GET", "/items");
  items.forEach((item) => (itemNames[item.id] = item.name));
  const tryOns = await api("GET", `/users/${getUserId()}/try-ons`);
  document.getElementById("tryons").innerHTML =
    tryOns.reverse().map(tryOnCard).join("") || '<p class="muted">Примерок пока нет.</p>';
}

async function initRoom() {
  const roomMessage = document.getElementById("room-message");
  const ordersMessage = document.getElementById("orders-message");
  const tryOnMessage = document.getElementById("tryon-message");
  const tryOnsMessage = document.getElementById("tryons-message");

  if (!getUserId()) {
    roomMessage.innerHTML = 'Чтобы пользоваться примерочной, заполните <a href="profile.html">анкету</a>.';
    return;
  }

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

  const tryOnButton = document.getElementById("tryon-button");
  const spinner = document.getElementById("tryon-spinner");
  const resultImage = document.getElementById("tryon-result");

  tryOnButton.addEventListener("click", async () => {
    const itemIds = [...document.querySelectorAll("#room-list [data-try]:checked")].map((box) => Number(box.dataset.try));
    if (itemIds.length === 0) {
      setMessage(tryOnMessage, "Отметьте галочкой вещи для примерки", true);
      return;
    }
    tryOnButton.disabled = true;
    spinner.hidden = false;
    resultImage.hidden = true;
    setMessage(tryOnMessage, "Генерируем примерку, это может занять до минуты…");
    try {
      const tryOn = await api("POST", `/users/${getUserId()}/try-ons`, { item_ids: itemIds });
      resultImage.src = tryOn.result_url;
      resultImage.hidden = false;
      setMessage(tryOnMessage, tryOn.source === "mock" ? "Режим mock: показано исходное фото" : "Готово");
    } catch (error) {
      setMessage(tryOnMessage, error.message, true);
    }
    spinner.hidden = true;
    tryOnButton.disabled = false;
    run(tryOnsMessage, loadTryOns);
  });

  document.getElementById("tryons").addEventListener("click", (event) => {
    const tryOnId = event.target.dataset.deleteTry;
    if (!tryOnId) return;
    run(tryOnsMessage, async () => {
      await api("DELETE", `/try-ons/${tryOnId}`);
      await loadTryOns();
    });
  });

  run(roomMessage, loadRoom);
  run(ordersMessage, loadOrders);
  run(tryOnsMessage, loadTryOns);
}

async function start() {
  await updateRoomCount();
  const page = document.body.dataset.page;
  if (page === "home") initHome();
  if (page === "catalog") initCatalog();
  if (page === "profile") initProfile();
  if (page === "room") initRoom();
}

start();
