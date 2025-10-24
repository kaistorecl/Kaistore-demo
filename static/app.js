async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const msg = await res.text().catch(()=>'');
    throw new Error(`HTTP ${res.status} – ${msg}`);
  }
  return res.json();
}

function money(n) {
  try { return n.toLocaleString("es-CL"); } catch { return n; }
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(()=> el.style.display = 'none', 2600);
}

async function loadProducts() {
  const grid = document.getElementById('grid');
  grid.innerHTML = '<p>Cargando productos…</p>';
  try {
    const products = await fetchJSON('/api/products/');
    if (!products.length) {
      grid.innerHTML = '<p>No hay productos aún. Crea uno desde <a href="/docs" style="color:#6ee7b7">/docs</a>.</p>';
      return;
    }
    grid.innerHTML = '';
    for (const p of products) {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <img src="${p.image_url}" alt="${p.title}" />
        <h3>${p.title}</h3>
        <p>${p.description ?? ''}</p>
        <div class="row">
          <div class="price">${p.currency} ${money(p.price)}</div>
          <button data-id="${p.id}">Comprar</button>
        </div>
      `;
      card.querySelector('button').addEventListener('click', () => checkout(p.id));
      grid.appendChild(card);
    }
  } catch (err) {
    grid.innerHTML = `<p>Error al cargar productos: ${err.message}</p>`;
  }
}

async function checkout(productId) {
  const btn = document.querySelector(`button[data-id="${productId}"]`);
  btn.disabled = true;
  btn.textContent = 'Creando orden…';
  try {
    const payload = {
      items: [{ product_id: productId, qty: 1 }],
      customer_email: 'test@example.com'
    };
    const data = await fetchJSON('/api/orders/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (data.checkout_url) {
      window.location.href = data.checkout_url; // redirige a Stripe
    } else {
      toast('No se recibió checkout_url');
    }
  } catch (err) {
    toast('Error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Comprar';
  }
}

loadProducts();
