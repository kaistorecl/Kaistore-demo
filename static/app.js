// app.js v12 – checkout robusto + debug visual

const $ = (sel) => document.querySelector(sel);
const productsEl = $("#products");
const toast = $("#toast");

function showToast(msg) {
  toast.textContent = msg;
  toast.style.display = "block";
  setTimeout(() => (toast.style.display = "none"), 6000);
}

function setVersion(v) {
  const el = document.getElementById("app-version");
  if (el) el.textContent = `(${v})`;
  document.title = `Kaistore • Demo ${v}`;
}
setVersion("v12");

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) {
    const detail = data && (data.detail || JSON.stringify(data));
    throw new Error(`HTTP ${res.status} ${res.statusText} :: ${detail || "sin detalle"}`);
  }
  return data;
}

function productCard(p) {
  return `
  <article class="card">
    <img src="${p.image_url}" alt="${p.title}" />
    <div class="card-body">
      <h3>${p.title}</h3>
      <p class="subtitle">${p.marketing_title || ""}</p>
      <div class="price">$${(p.price || 0).toLocaleString("es-CL")}</div>
      <button class="btn-buy" data-id="${p.id}">Comprar ahora</button>
    </div>
  </article>`;
}

let PUBLISHED = [];

async function loadProducts() {
  const data = await fetchJSON("/api/products/published");
  PUBLISHED = data || [];
  if (!Array.isArray(PUBLISHED) || !PUBLISHED.length) {
    productsEl.innerHTML = `<p style="opacity:.7">No hay productos publicados todavía 👋</p>`;
    return;
  }
  productsEl.innerHTML = PUBLISHED.map(productCard).join("");
  bindBuyButtons();
}

function bindBuyButtons() {
  productsEl.querySelectorAll(".btn-buy").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.id);
      btn.disabled = true;
      btn.textContent = "Redirigiendo…";

      try {
        // INTENTO #1: por product_id/qty
        const payload1 = { items: [{ product_id: id, qty: 1 }] };
        const out1 = await fetchJSON("/api/orders/checkout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload1),
        });
        if (out1 && out1.url) {
          window.location = out1.url;
          return;
        }
        // Si no vino url, forzamos error para caer al catch
        throw new Error(`Respuesta inesperada: ${JSON.stringify(out1)}`);
      } catch (e1) {
        // INTENTO #2 (fallback): enviar datos sueltos
        try {
          const p = PUBLISHED.find((x) => x.id === id);
          if (!p) throw new Error("Producto no encontrado en memoria.");

          const payload2 = {
            items: [{
              title: p.title,
              price: p.price,
              quantity: 1,
              currency: p.currency || "CLP",
            }],
          };

          const out2 = await fetchJSON("/api/orders/checkout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload2),
          });

          if (out2 && out2.url) {
            window.location = out2.url;
            return;
          }
          throw new Error(`Respuesta inesperada: ${JSON.stringify(out2)}`);
        } catch (e2) {
          console.error("Checkout error:", e1, e2);
          showToast(`No se pudo iniciar el pago: ${e2.message || e1.message}`);
          btn.disabled = false;
          btn.textContent = "Comprar ahora";
        }
      }
    });
  });
}

window.addEventListener("DOMContentLoaded", loadProducts);
