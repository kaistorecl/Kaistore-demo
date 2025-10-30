// static/app.js  v14
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
    let msg = "Error";
    try { const j = await res.json(); msg = j.detail || JSON.stringify(j); } catch {}
    throw new Error(msg);
  }
  return res.json();
}

function formatCLP(value) {
  try {
    return new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(value);
  } catch {
    return `$${value}`;
  }
}

function productCard(p) {
  const img = p.image_url || p.image || "https://images.unsplash.com/photo-1519682337058-a94d519337bc?w=1200";
  const title = p.title || (p.preview && p.preview.marketing_title) || "Producto";
  const price = p.price || (p.preview && p.preview.price) || 0;

  const card = document.createElement("div");
  card.className = "card";

  card.innerHTML = `
    <img class="card-img" src="${img}" alt="${title}">
    <div class="card-body">
      <h3 class="card-title">${title}</h3>
      <p class="card-price">${formatCLP(price)}</p>
      <button class="buy-btn" data-id="${p.id}">Comprar ahora</button>
    </div>
  `;
  card.querySelector(".buy-btn").addEventListener("click", () => startCheckout(p.id));
  return card;
}

async function startCheckout(productId) {
  const btn = document.querySelector(`.buy-btn[data-id="${productId}"]`);
  if (btn) { btn.disabled = true; btn.textContent = "Redirigiendo…"; }
  try {
    // 👇 ESTE ES EL FORMATO QUE ESPERA TU API
    const body = { items: [{ product_id: Number(productId), qty: 1 }] };
    const data = await fetchJSON(`${API}/orders/checkout`, { method: "POST", body: JSON.stringify(body) });
    if (data && data.url) {
      window.location.href = data.url; // Stripe Checkout
    } else {
      throw new Error("Respuesta sin URL de pago");
    }
  } catch (err) {
    console.error("Checkout error:", err);
    toast("No se pudo iniciar el pago");
    if (btn) { btn.disabled = false; btn.textContent = "Comprar ahora"; }
  }
}

function toast(text) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = text;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
}

async function loadProducts() {
  const grid = document.getElementById("product-grid");
  grid.innerHTML = '<div class="loading">Cargando…</div>';
  try {
    const products = await fetchJSON(`${API}/products/published`);
    grid.innerHTML = "";
    if (!products || !products.length) {
      grid.innerHTML = `<p class="empty">No hay productos publicados todavía 👋</p>`;
      return;
    }
    products.forEach((p) => grid.appendChild(productCard(p)));
  } catch (err) {
    console.error(err);
    grid.innerHTML = `<p class="error">No se pudieron cargar los productos</p>`;
  }
}

window.addEventListener("DOMContentLoaded", loadProducts);
