// Helpers UI
function showToast(msg) {
  // si tienes un toast propio, úsalo; aquí un alert no bloqueante simple
  console.log("TOAST:", msg);
}

function showDebug(obj) {
  const el = document.getElementById("debug");
  if (!el) return;
  el.style.display = "block";
  el.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
}

// Renderiza la grilla con los publicados
async function loadProducts() {
  const grid = document.getElementById("grid");
  grid.innerHTML = "<div class='loading'>Cargando…</div>";

  try {
    const r = await fetch("/api/products/published");
    const items = await r.json();

    if (!Array.isArray(items) || items.length === 0) {
      grid.innerHTML = "<p style='padding:16px'>No hay productos publicados.</p>";
      return;
    }

    grid.innerHTML = items.map(p => {
      const title = p.title || p.marketing_title || "Producto";
      const subtitle = p.marketing_title || p.title || "";
      const price = (p.price ?? 0).toLocaleString("es-CL");
      const img = p.image_url || (p.image_urls && p.image_urls[0]) || "https://picsum.photos/seed/stock/1200/800";

      return `
        <article class="card">
          <img src="${img}" alt="${title}" class="cover" />
          <div class="card-body">
            <h3>${title}</h3>
            <p class="subtle">${subtitle}</p>
            <div class="price">$${price}</div>
            <button class="btn btn-primary buy-btn" data-product-id="${p.id}">Comprar ahora</button>
          </div>
        </article>
      `;
    }).join("");

    // Wire botones
    grid.querySelectorAll(".buy-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const pid = btn.getAttribute("data-product-id");
        if (!pid) {
          showToast("No se encontró el product_id");
          showDebug({ error: "botón sin data-product-id" });
          return;
        }
        await pay(pid);
      });
    });
  } catch (e) {
    grid.innerHTML = "<p style='padding:16px'>Error cargando productos.</p>";
    showDebug({ step: "loadProducts", error: String(e) });
  }
}

// Llama al checkout con fallback por querystring (sin body)
async function pay(productId) {
  try {
    const url = `/api/orders/checkout?product_id=${encodeURIComponent(productId)}&qty=1`;

    const r = await fetch(url, { method: "POST" });
    const contentType = r.headers.get("content-type") || "";

    // Si viene JSON, parseamos; si no, leemos texto para depurar
    let data = null;
    if (contentType.includes("application/json")) {
      data = await r.json();
    } else {
      const txt = await r.text();
      data = { raw: txt };
    }

    if (!r.ok) {
      showToast("No se pudo iniciar el pago");
      showDebug({ step: "checkout", status: r.status, url, response: data });
      return;
    }

    if (data && data.url) {
      window.location.href = data.url;
      return;
    }

    showToast("Respuesta inesperada del servidor");
    showDebug({ step: "checkout", status: r.status, url, response: data });
  } catch (e) {
    showToast("No se pudo iniciar el pago");
    showDebug({ step: "checkout-catch", error: String(e) });
  }
}

document.addEventListener("DOMContentLoaded", loadProducts);
