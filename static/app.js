// static/app.js

// 1. Función para formatear CLP tipo "$5.990"
function formatPriceCLP(num) {
  // num viene como 5990 (float o int)
  try {
    const intVal = Math.round(Number(num));
    return "$" + intVal.toLocaleString("es-CL");
  } catch (e) {
    return "$" + num;
  }
}

// 2. Renderizar UNA tarjeta de producto
function renderProductCard(product) {
  // product viene del backend /api/products/published
  // Ejemplo:
  // {
  //   "id": 1,
  //   "title_marketing": "Organizador plegable premium...",
  //   "short_bullets": [],
  //   "price": 5990,
  //   "currency": "CLP",
  //   "image_url": "https://...."
  // }

  const card = document.createElement("div");
  card.className = "product-card";
  card.style.maxWidth = "700px";
  card.style.width = "100%";
  card.style.borderRadius = "8px";
  card.style.overflow = "hidden";
  card.style.border = "1px solid #e5e7eb";
  card.style.boxShadow = "0 1px 2px rgb(0 0 0 / 0.05)";
  card.style.backgroundColor = "#fff";

  // imagen de producto
  const img = document.createElement("img");
  img.src = product.image_url || "https://via.placeholder.com/800x800?text=Producto";
  img.alt = product.title_marketing || "Producto";
  img.style.width = "100%";
  img.style.height = "auto";
  img.style.display = "block";

  // contenedor info
  const info = document.createElement("div");
  info.style.padding = "16px";
  info.style.borderTop = "1px solid #e5e7eb";

  // título principal (marketing/title)
  const titleEl = document.createElement("div");
  titleEl.style.fontSize = "16px";
  titleEl.style.fontWeight = "600";
  titleEl.style.color = "#111827";
  titleEl.style.marginBottom = "6px";
  titleEl.textContent = product.title_marketing || product.title || "Producto sin título";

  // descripción corta debajo del título
  const descEl = document.createElement("div");
  descEl.style.fontSize = "14px";
  descEl.style.color = "#4b5563";
  descEl.style.marginBottom = "8px";
  // usamos title_marketing otra vez si no tenemos más texto
  descEl.textContent =
    product.title_marketing || product.title || "Descripción no disponible";

  // precio
  const priceEl = document.createElement("div");
  priceEl.style.fontSize = "14px";
  priceEl.style.fontWeight = "600";
  priceEl.style.color = "#111827";
  priceEl.style.marginBottom = "12px";
  priceEl.textContent = formatPriceCLP(product.price || 0);

  // botón comprar
  const btn = document.createElement("button");
  btn.className = "checkout-btn";
  btn.style.width = "100%";
  btn.style.display = "block";
  btn.style.backgroundColor = "#1d4ed8";
  btn.style.color = "#fff";
  btn.style.fontSize = "14px";
  btn.style.fontWeight = "500";
  btn.style.padding = "10px 12px";
  btn.style.border = "0";
  btn.style.borderRadius = "4px";
  btn.style.cursor = "pointer";
  btn.style.textAlign = "center";
  btn.textContent = "Comprar ahora";

  // handler click -> llama /api/orders/checkout
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.style.opacity = "0.6";
    btn.textContent = "Redirigiendo…";

    try {
      // armamos el payload como lo espera tu backend:
      // Opción 1 soportada (por product_id):
      // { "items": [ { "product_id": 3, "qty": 1 } ] }

      const payload = {
        items: [
          {
            product_id: product.id,
            qty: 1,
          },
        ],
      };

      const resp = await fetch("/api/orders/checkout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        // ejemplo 400 {detail:"JSON inválido"} u otro error
        const errText = await resp.text();
        alert("No se pudo iniciar el pago.\n" + errText);
        btn.disabled = false;
        btn.style.opacity = "1";
        btn.textContent = "Comprar ahora";
        return;
      }

      // si OK, deberíamos recibir { "checkout_url": "https://checkout.stripe.com/..." }
      const data = await resp.json();
      if (data.checkout_url) {
        // redirigimos a Stripe Checkout
        window.location.href = data.checkout_url;
      } else {
        alert("No se recibió checkout_url desde el servidor.");
        btn.disabled = false;
        btn.style.opacity = "1";
        btn.textContent = "Comprar ahora";
      }
    } catch (err) {
      console.error(err);
      alert("Error de red o JS al crear checkout.");
      btn.disabled = false;
      btn.style.opacity = "1";
      btn.textContent = "Comprar ahora";
    }
  });

  // línea azul del botón separada con borde-top
  const buttonWrapper = document.createElement("div");
  buttonWrapper.style.borderTop = "1px solid #e5e7eb";
  buttonWrapper.style.backgroundColor = "#eff6ff";
  buttonWrapper.style.padding = "12px 16px";
  buttonWrapper.appendChild(btn);

  // metemos todo en la card
  info.appendChild(titleEl);
  info.appendChild(descEl);
  info.appendChild(priceEl);

  card.appendChild(img);
  card.appendChild(info);
  card.appendChild(buttonWrapper);

  return card;
}

// 3. Cargar productos publicados
async function loadProducts() {
  const container = document.getElementById("products-container");
  const loadingMsg = document.getElementById("loading-msg");

  try {
    const resp = await fetch("/api/products/published");
    if (!resp.ok) {
      throw new Error("No se pudo cargar catálogo (" + resp.status + ")");
    }
    const products = await resp.json();

    // limpiamos loading
    if (loadingMsg) {
      loadingMsg.remove();
    }

    if (!products || products.length === 0) {
      const emptyMsg = document.createElement("div");
      emptyMsg.style.color = "#6b7280";
      emptyMsg.style.fontSize = "14px";
      emptyMsg.style.textAlign = "center";
      emptyMsg.textContent = "No hay productos publicados todavía.";
      container.appendChild(emptyMsg);
      return;
    }

    // Pintamos cada producto
    products.forEach((p) => {
      const cardEl = renderProductCard(p);
      container.appendChild(cardEl);
    });
  } catch (err) {
    console.error(err);
    if (loadingMsg) {
      loadingMsg.textContent =
        "Error cargando productos. Intenta recargar la página.";
    }
  }
}

// 4. ejecutar al cargar la página
document.addEventListener("DOMContentLoaded", loadProducts);
