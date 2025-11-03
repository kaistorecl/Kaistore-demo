// static/app.js
// Front de la tienda: lista productos y abre Stripe Checkout

const API_BASE = '/api';

function formatCLP(v) {
  try {
    return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(v);
  } catch {
    return `$${(v || 0).toLocaleString('es-CL')}`;
  }
}

function toast(msg) {
  // Aviso simple abajo (sin dependencias)
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = `
    position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%);
    background: rgba(0,0,0,.85); color: #fff; padding: 10px 14px; border-radius: 8px;
    font-size: 14px; z-index: 9999;
  `;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2600);
}

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

function productCard(p) {
  const card = document.createElement('div');
  card.className = 'card';

  card.innerHTML = `
    <img class="card-img" src="${p.image_url || '/static/placeholder.jpg'}" alt="${p.marketing_title || 'Producto'}" />
    <div class="card-body">
      <h3 class="card-title">${p.marketing_title || p.title || 'Producto'}</h3>
      <p class="card-desc">${p.short_benefit || p.description || ''}</p>
      <div class="card-price">${formatCLP(p.price || 0)}</div>
      <button class="btn-primary">Comprar ahora</button>
    </div>
  `;

  const btn = card.querySelector('button');
  btn.addEventListener('click', async () => {
    try {
      btn.disabled = true;
      btn.textContent = 'Redirigiendo…';

      // SIEMPRE enviamos 'clp' en minúsculas a Stripe
      const payload = {
        items: [
          {
            title: p.marketing_title || p.title || 'Producto',
            price: Number(p.price || 0),
            quantity: 1,
            currency: 'clp',
            image_url: p.image_url || null,
          },
        ],
      };

      const data = await fetchJSON(`${API_BASE}/orders/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (data && data.url) {
        window.location.href = data.url;
      } else {
        throw new Error('sin_url');
      }
    } catch (e) {
      console.error(e);
      toast('No se pudo iniciar el pago');
      btn.disabled = false;
      btn.textContent = 'Comprar ahora';
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
    if (!items || !items.length) {
      grid.innerHTML = '<div class="grid-empty">No hay productos publicados todavía 👋</div>';
      return;
    }
    items.forEach((p) => grid.appendChild(productCard(p)));
  } catch (e) {
    console.error(e);
    document.getElementById('products').innerHTML =
      '<div class="grid-empty">Error cargando productos</div>';
  }
}

document.addEventListener('DOMContentLoaded', loadProducts);
