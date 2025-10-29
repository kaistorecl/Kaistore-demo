// app.js
// Frontend simple para la tienda
// - carga productos publicados desde /api/products/published
// - muestra cada producto en una card
// - al hacer click en "Comprar ahora", crea una sesión de pago en Stripe
//   llamando al backend /api/orders/checkout con el formato correcto

// URL base del backend (tu Render)
const API_BASE = "https://kaistore-demo.onrender.com/api";

// contenedor donde van las cards
const productsContainer = document.getElementById("products-container");

// util: formatear CLP bonito
function formatPriceCLP(value) {
  // value viene como número (por ej 5990)
  try {
    return new Intl.NumberFormat("es-CL", {
      style: "currency",
      currency: "CLP",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  } catch (e) {
    // fallback si Intl no pesca
    return "$" + value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }
}

// crea el HTML de UNA tarjeta de producto
function renderProductCard(prod) {
  // prod tiene este formato (desde /api/products/published):
  // {
  //   "id": 1,
  //   "title_marketing": "Organizador...",
  //   "short_bullets": [],
  //   "price": 5990,
  //   "currency": "CLP",
  //   "image_urls": ["https://..."]
  // }

  const title = prod.title_marketing || "Producto";
  const desc =
    prod.short_bullets && prod.short_bullets.length > 0
      ? prod.short_bullets[0]
      : prod.title_marketing || "";
  const priceCLP = formatPriceCLP(prod.price || 0);

  // imagen: usamos la primera si existe, si no un placeholder
  let imgSrc =
    (prod.image_urls && prod.image_urls[0]) ||
    "https://via.placeholder.com/800x800?text=Producto";

  // creamos elemento raíz
  const card = document.createElement("div");
  card.className =
    "product-card max-w-xl w-full bg-white border border-gray-200 rounded shadow flex flex-col overflow-hidden";

  card.innerHTML = `
    <img
      src="${imgSrc}"
      alt="${title}"
      class="w-full h-auto object-cover"
      style="aspect-ratio: 1/1; object-fit: cover;"
    />

    <div class="p-4 flex flex-col gap-2">
      <div class="text-base font-semibold text-gray-900 leading-snug">
        ${title}
      </div>
      <div class="text-sm text-gray-600 leading-snug">
        ${desc}
      </div>
      <div class="text-sm font-bold text-gray-900">
        ${priceCLP}
      </div>

      <button
        class="checkout-btn w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2 px-4 rounded-md transition-colors"
        data-product-id="${prod.id}"
      >
        Comprar ahora
      </button>
    </div>
  `;

  // agregamos listener al botón "Comprar ahora"
  const btn = card.querySelector(".checkout-btn");
  btn.addEventListener("click", () => {
    createCheckout(prod.id);
  });

  return card;
}

// pide la lista de productos publicados al backend
async function loadProducts() {
  try {
    const res = await fetch(`${API_BASE}/products/published`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!res.ok) {
      console.error("Error cargando productos:", res.status, res.statusText);
      productsContainer.innerHTML =
        '<p style="color:red;">No se pudieron cargar los productos 😢</p>';
      return;
    }

    const data = await res.json();

    // data debería ser un array tipo:
    // [
    //   {
    //     "id": 1,
    //     "title_marketing": "...",
    //     "short_bullets": [],
    //     "price": 5990,
    //     "currency": "CLP",
    //     "image_urls": ["https://..."]
    //   }
    // ]

    productsContainer.innerHTML = ""; // limpio por si había algo

    if (!Array.isArray(data) || data.length === 0) {
      productsContainer.innerHTML =
        '<p class="text-gray-500">No hay productos publicados aún 🙃</p>';
      return;
    }

    data.forEach((prod) => {
      const cardEl = renderProductCard(prod);
      productsContainer.appendChild(cardEl);
    });
  } catch (err) {
    console.error("Excepción cargando productos:", err);
    productsContainer.innerHTML =
      '<p style="color:red;">Error al cargar productos 😢</p>';
  }
}

// llama al backend para crear la sesión de checkout en Stripe
async function createCheckout(productId) {
  try {
    // armamos el payload EXACTO que el backend espera:
    // { "items": [ { "product_id": <id>, "qty": 1 } ] }
    const payload = {
      items: [
        {
          product_id: productId,
          qty: 1,
        },
      ],
    };

    const res = await fetch(`${API_BASE}/orders/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      console.error("Error creando sesión de checkout:", res.status);
      alert("No se pudo iniciar el pago 😢");
      return;
    }

    // el backend debería responder algo como:
    // { "checkout_url": "https://checkout.stripe.com/pay/..." }
    const data = await res.json();

    if (data && data.checkout_url) {
      // redirigimos al checkout de Stripe
      window.location.href = data.checkout_url;
    } else {
      console.error("Respuesta inesperada:", data);
      alert("Hubo un problema creando el pago 😢");
    }
  } catch (err) {
    console.error("Excepción creando checkout:", err);
    alert("Error de red creando el pago 😢");
  }
}

// cuando carga la página, traemos los productos
document.addEventListener("DOMContentLoaded", loadProducts);
