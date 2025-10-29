// static/app.js
document.addEventListener("DOMContentLoaded", () => {
  const buyBtn = document.getElementById("buyBtn");

  function readProductId() {
    const fromBtn = buyBtn?.getAttribute("data-product-id");
    if (fromBtn) return Number(fromBtn);
    const card = document.querySelector("[data-product-id]");
    if (card) return Number(card.getAttribute("data-product-id"));
    const el = document.getElementById("productId");
    if (el && el.value) return Number(el.value);
    return null;
  }

  async function createCheckoutSession(productId) {
    // Si tu endpoint acepta "qty", usa este:
    let body = { items: [{ product_id: Number(productId), qty: 1 }] };

    // Si al probar te devuelve 400 JSON inválido, cambia a:
    // body = { items: [{ product_id: Number(productId), quantity: 1 }] };

    const resp = await fetch("/api/orders/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(body)
    });

    const raw = await resp.text();
    if (!resp.ok) throw new Error(`status=${resp.status} body=${raw}`);

    let data = null;
    try { data = JSON.parse(raw); } catch { throw new Error("Respuesta no-JSON: " + raw); }

    const url = data.url || data.checkout_url;
    if (!url) throw new Error("Backend no entregó URL de checkout: " + raw);
    return url;
  }

  if (buyBtn) {
    buyBtn.addEventListener("click", async () => {
      buyBtn.disabled = true; buyBtn.style.opacity = "0.7"; buyBtn.textContent = "Procesando...";
      try {
        const productId = readProductId();
        if (!productId) throw new Error("No se pudo determinar el product_id mostrado.");
        const checkoutUrl = await createCheckoutSession(productId);
        window.location.href = checkoutUrl;
      } catch (err) {
        alert("No se pudo iniciar el pago.\n" + (err?.message || err));
      } finally {
        buyBtn.disabled = false; buyBtn.style.opacity = "1"; buyBtn.textContent = "Comprar ahora";
      }
    });
  }
});
