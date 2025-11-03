// static/app.js
const API_BASE = '/api';

function formatCLP(v) {
  try { return new Intl.NumberFormat('es-CL',{style:'currency',currency:'CLP',maximumFractionDigits:0}).format(v); }
  catch { return `$${(v||0).toLocaleString('es-CL')}`; }
}

function toast(msg) {
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = `
    position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%);
    background: rgba(0,0,0,.85); color: #fff; padding: 10px 14px; border-radius: 8px;
    font-size: 14px; z-index: 9999; max-width: 90%; text-align: center;
  `;
  document.body.appendChild(t);
  setTimeout(()=>t.remove(), 2800);
}

async function fetchJSON(url, opts={}) {
  const res = await fetch(url, opts);
  let data = null;
  try { data = await res.json(); } catch {}
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || `HTTP ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function productCard(p) {
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = `
    <img class="card-img" src="${p.image_url || '/static/placeholder.jpg'}" alt="${p.marketing_title || 'Producto'}" />
    <div class="card-body">
      <h3 class="card-title">${p.marketing_title || p.title || 'Producto'}</h3>
      <p class="card-desc">${p.short_bullets || p.description || ''}</p>
      <div class="card-price">${formatCLP(p.price || 0)}</div>
      <button class="btn-primary">Comprar ahora</button>
    </div>
  `;
  const btn = card.querySelector('button');
  btn.addEventListener('click', async () => {
    try {
      btn.disabled = true; btn.textContent = 'Redirigiendo…';
      const payload = {
        items: [{
          title: p.marketing_title || p.title || 'Producto',
          price: Number(p.price || 0),
          quantity: 1,
          currency: 'clp',                    // <- minúsculas siempre
          image_url: p.image_url || null,
        }],
      };
      const data = await fetchJSON(`${API_BASE}/orders/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (data && data.url) { window.location.href = data.url; return; }
      throw new Error('Respuesta sin URL de checkout');
    } catch (e) {
      console.error('checkout error:', e);
      toast(e.message?.toString().slice(0,160) || 'No se pudo iniciar el pago');
      btn.disabled = false; btn.textContent = 'Comprar ahora';
    }
  });
  return card;
}

async function loadProducts() {
  const grid = document.getElementById('products');
  grid.innerHTML = '<div class="grid-empty">Cargando…</div>';
  try {
    const items = await fetchJSON(`${API_BASE}/products/published`);
    grid.innerHTML = '';
    if (!items?.length) {
      grid.innerHTML = '<div class="grid-empty">No hay productos publicados todavía 👋</div>';
      return;
    }
    items.forEach(p => grid.appendChild(productCard(p)));
  } catch (e) {
    console.error(e);
    grid.innerHTML = '<div class="grid-empty">Error cargando productos</div>';
  }
}

document.addEventListener('DOMContentLoaded', loadProducts);
