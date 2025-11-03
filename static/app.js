// static/app.js  v15
const API = "/api";

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, {
    ...opts,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j.detail || JSON.stringify(j);
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

function formatCLP(v) {
  try {
    return new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(v);
  } catch { return `$${v}`; }
}

function productCard(p) {
  const img = p.image_url || p.image || "https://images.unsplash.com/photo-1519682337058-a94d519337bc?w=1200";
  const title = p.title || (p.preview && p.preview.marketing_title) || "Producto";
  const price = p.price || (p.preview && p.preview.price) || 0;

  const el = document.createElement("div");
  el.className = "card";
  el.innerHTML = `
    <img class="card-img" src="${img}" alt="${title}">
    <div class="card-body">
      <h3 class="card-title">${title}</h3>
      <p class="card-price">${formatCLP(price)}</p>
      <button class="buy-btn" data-id="${p.id}">Comprar ahora (v15)</button>
    </div>
  `;
  el.querySelector(".buy-btn").addEventListener("click", () => startCheckout(p.id));
  return el;
}

async function startCheckout(productId) {
  const btn = document.querySelector(`.buy-btn[data-id="${productId}"]`);
  if (btn) { btn.disabled = true; btn.textContent = "Redirigiendo…"; }
  try {
    // Formato que espera el backend
    const body = { items: [{ product_id: Number(productId), qty: 1 }] };
    const data = await fetchJSON(`${API}/orders/checkout`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (data && data.url) window.location.href = data.url;
    else throw new Error("Respuesta sin URL de pago");
  } catch (err) {
    console.error("Checkout error:", err);
    toast(`No se pudo iniciar el pago: ${err.message}`);
    if (btn) { btn.disabled = false; btn.textContent = "Comprar ahora (v15)"; }
  }
}

function toast(text) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = text;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

async function loadProducts() {
  const grid = document.getElementById("product-grid");
  grid.innerHTML = '<div class="loading">Cargando…</div>';
  try {
    const products = await fetchJSON(`${API}/products/published`);
    grid.innerHTML = "";
    if (!products?.length) {
      grid.innerHTML = `<p class="empty">No hay productos publicados todavía 👋</p>`;
      return;
    }
    products.forEach(p => grid.appendChild(productCard(p)));
  } catch (e) {
    console.error(e);
    grid.innerHTML = `<p class="error">No se pudieron cargar los productos</p>`;
  }
}

window.addEventListener("DOMContentLoaded", loadProducts);
