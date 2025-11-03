// static/app.js  v16
console.log("static/app.js v16");

const $ = (sel, p = document) => p.querySelector(sel);
const $$ = (sel, p = document) => [...p.querySelectorAll(sel)];

const API = {
  list: async () => {
    const r = await fetch('/api/products/published', { headers: { 'accept': 'application/json' }});
    if (!r.ok) throw new Error('No se pudo listar productos');
    return r.json();
  },
  checkout: async (items) => {
    const payload = { items }; // formato suelto: [{ title, price, quantity, currency }]
    const r = await fetch('/api/orders/checkout', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'accept': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!r.ok) {
      const txt = await r.text().catch(()=> '');
      throw new Error(`Checkout falló (${r.status}): ${txt || 'respuesta no válida'}`);
    }
    return r.json();
  }
};

function cardHTML(p) {
  const img = p.image_url || 'https://picsum.photos/seed/kaistore/800/600';
  const title = p.marketing_title || p.title || 'Producto';
  const price = Number(p.price || 0);
  const currency = p.currency || 'CLP';
  return `
    <article class="card">
      <img src="${img}" alt="${title}">
      <div class="bx">
        <h3 style="margin:0 0 6px 0">${title}</h3>
        <p class="muted" style="margin:0 0 10px 0">${title}</p>
        <div style="font-weight:700;margin-bottom:10px">$${price.toLocaleString('es-CL')}</div>
        <button class="btn buy"
          data-title="${title.replace(/"/g,'&quot;')}"
          data-price="${price}"
          data-currency="${currency}">Comprar ahora (v16)</button>
      </div>
    </article>
  `;
}

async function mount() {
  try {
    const data = await API.list();
    const grid = $('#products');
    if (!data || data.length === 0) {
      $('#empty').style.display = 'block';
      return;
    }
    grid.innerHTML = data.map(cardHTML).join('');

    // Buscar
    $('#q').addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      $$('.card').forEach(c => {
        const t = $('.bx h3', c).textContent.toLowerCase();
        c.style.display = t.includes(q) ? '' : 'none';
      });
    });

    // Delegación de eventos para comprar
    grid.addEventListener('click', async (ev) => {
      const btn = ev.target.closest('.buy');
      if (!btn) return;

      btn.disabled = true; btn.textContent = 'Creando pago…';
      try {
        // Usamos el formato “datos sueltos” que tu API acepta:
        const item = {
          title: btn.dataset.title,
          price: Number(btn.dataset.price),
          quantity: 1,
          currency: btn.dataset.currency || 'CLP'
        };
        const res = await API.checkout([item]);
        if (res && res.url) {
          location.href = res.url; // redirige a Stripe
        } else {
          throw new Error('La API no devolvió URL de pago');
        }
      } catch (err) {
        console.error(err);
        alert('No se pudo iniciar el pago: ' + err.message);
      } finally {
        btn.disabled = false; btn.textContent = 'Comprar ahora (v16)';
      }
    });

  } catch (e) {
    console.error(e);
    alert('Error cargando tienda: ' + e.message);
  }
}

document.addEventListener('DOMContentLoaded', mount);
