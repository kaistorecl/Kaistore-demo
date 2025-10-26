import asyncio
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from db import Base, engine, SessionLocal
from config import settings

# importa tus routers existentes (orders, payments, etc.)
from routers import orders, payments

# importa los routers nuevos que definimos
from routers import products, admin_products


# ---------------------------------
# Inicializar FastAPI
# ---------------------------------

app = FastAPI(
    title="Kaistore API + Front",
    description="Catálogo dinámico + Checkout + Admin draft/publish",
    version="0.2.0",
)

# CORS abierto para que el front pueda hacer fetch a las APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # en producción puedes cerrar esto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------
# DB init en startup
# ---------------------------------

@app.on_event("startup")
def on_startup():
    # crea tablas si no existen
    Base.metadata.create_all(bind=engine)


# ---------------------------------
# Montar routers API
# ---------------------------------

# catálogo público dinámico
app.include_router(products.router)

# endpoints admin para ver drafts y publicar productos
app.include_router(admin_products.router)

# los que ya tenías para órdenes y pagos (Stripe sandbox)
app.include_router(orders.router)
app.include_router(payments.router)


# ---------------------------------
# Página principal (Home / Catálogo)
# ---------------------------------

@app.get("/", response_class=HTMLResponse)
async def home():
    # Esta página ahora hace fetch a /api/products/published
    # y pinta las cards en base a esa respuesta.
    return """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Kaistore – Demo</title>
    <link rel="stylesheet" href="/static/style.css"/>
</head>
<body>

<header class="header">
    <div class="container" style="display:flex; align-items:center;">
        <div class="brand">
            <span class="dot"></span>
            <h1>Kaistore – Demo</h1>
        </div>
        <div class="controls">
            <label class="search">
                🔍
                <input id="q" placeholder="Buscar productos…"/>
            </label>
        </div>
    </div>
</header>

<main class="container">
    <div id="grid" class="grid"></div>
    <p class="footer">Sandbox · Pagos de prueba en Stripe</p>
</main>

<div id="toast" class="toast"></div>

<script>
// ------------------------------
// Referencias
// ------------------------------
const $grid  = document.getElementById("grid");
const $q     = document.getElementById("q");
const $toast = document.getElementById("toast");

// ------------------------------
// Formateador CLP / moneda
// ------------------------------
function formatPrice(amount, currency){
    // algunos países no usan decimales (CLP normalmente no)
    const zeroDecimal = new Set([
        "BIF","CLP","DJF","GNF","JPY","KMF","KRW","MGA","PYG","RWF",
        "UGX","VND","VUV","XAF","XOF","XPF"
    ]);
    const curr = (currency || "CLP").toUpperCase();
    const isZero = zeroDecimal.has(curr);
    const value = isZero ? amount : (amount || 0);
    const scaled = isZero ? value : value; // acá asumimos que ya guardas price final, no centavos

    try{
        return new Intl.NumberFormat("es-CL", {
            style:"currency",
            currency: curr,
            minimumFractionDigits: isZero ? 0 : 2,
            maximumFractionDigits: isZero ? 0 : 2
        }).format(scaled || 0);
    }catch(e){
        return `${scaled || 0} ${curr}`;
    }
}

// ------------------------------
// Toast simple
// ------------------------------
function toast(msg){
    $toast.textContent = msg;
    $toast.classList.add("show");
    setTimeout(()=> $toast.classList.remove("show"), 1800);
}

// ------------------------------
// Cargar productos publicados
// ------------------------------
async function fetchProducts(){
    console.log("→ Fetch /api/products/published");
    const res = await fetch("/api/products/published");
    if(!res.ok){
        const txt = await res.text().catch(()=> "");
        throw new Error(`No se pudieron cargar productos (HTTP ${res.status}): ${txt}`);
    }
    return await res.json();
}

// ------------------------------
// Renderizar productos en el grid
// ------------------------------
function render(products){
    if(!products || products.length === 0){
        $grid.innerHTML = `<div style="color:#999; text-align:center; padding:2rem;">
            No hay productos publicados todavía.
        </div>`;
        return;
    }

    const term = ($q.value || "").toLowerCase().trim();
    const list = term
        ? products.filter(p =>
            (p.title_marketing||"").toLowerCase().includes(term) ||
            (p.short_bullets||[]).join(" ").toLowerCase().includes(term)
        )
        : products;

    $grid.innerHTML = list.map(p => {
        const img = (p.image_urls && p.image_urls.length > 0)
            ? p.image_urls[0]
            : "https://via.placeholder.com/400x400?text=Producto";

        const desc = (p.short_bullets && p.short_bullets.length > 0)
            ? p.short_bullets[0]
            : "";

        return `
        <article class="card" style="animation: fadein .4s ease;">
            <img class="img"
                 src="${img}"
                 alt="${p.title_marketing || 'Producto'}"
                 onerror="this.src='https://via.placeholder.com/400x400?text=Producto';"/>
            <div class="body">
                <div class="row">
                    <div class="price">${formatPrice(p.price, p.currency)}</div>
                </div>

                <div class="title">${p.title_marketing || ''}</div>
                <div class="desc">${desc}</div>

                <div class="row">
                    <button class="btn" onclick="buy(${p.id})">🛒 Comprar</button>
                </div>
            </div>
        </article>
        `;
    }).join("");

    // Animación fade-in CSS inline
    const style = document.createElement("style");
    style.textContent = `
    @keyframes fadein {
        from { opacity:0; transform:translateY(10px); }
        to   { opacity:1; transform:translateY(0);    }
    }`;
    document.head.appendChild(style);
}

// ------------------------------
// Proceso de compra
// Llama a tu backend de checkout existente (/api/orders/checkout)
// ------------------------------
async function buy(productId){
    try{
        const body = { items: [{ product_id: productId, qty: 1 }] };
        const res = await fetch("/api/orders/checkout", {
            method: "POST",
            headers: { "Content-Type":"application/json" },
            body: JSON.stringify(body)
        });

        if(!res.ok){
            const txt = await res.text().catch(()=> "");
            throw new Error(`Error creando checkout (HTTP ${res.status}): ${txt}`);
        }
        const data = await res.json();
        if(data.checkout_url){
            location.href = data.checkout_url;
        }else{
            toast("No se recibió URL de pago");
        }
    }catch(e){
        console.error(e);
        toast("No se pudo iniciar el pago");
    }
}

// ------------------------------
// Inicializar página
// ------------------------------
(async function init(){
    $grid.innerHTML = `<div style="color:#9aa4b2; text-align:center; padding:2rem;">Cargando…</div>`;
    try{
        const products = await fetchProducts();
        render(products);
        $q.addEventListener("input", () => render(products));
    }catch(e){
        console.error("init error:", e);
        $grid.innerHTML = `<div style="color:#ff5855; text-align:center; padding:2rem;">
            Error cargando productos
        </div>`;
    }
})();
</script>

</body>
</html>
"""


# ---------------------------------
# Healthcheck sencillo
# ---------------------------------

@app.get("/api/health")
async def health():
    return {"ok": True}


# ---------------------------------
# Ruta de éxito de pago (Stripe sandbox)
# ---------------------------------

@app.get("/success", response_class=HTMLResponse)
async def success():
    # Nota: reutilizo tu lógica original de /success pero condensada
    # para evitar que se pierda. La idea es que el front lea los detalles
    # del pago con /api/payments/session/{id}.
    return """
<html>
<head><title>Pago completado</title></head>
<body style="font-family:sans-serif; background:#111; color:#eee; padding:2rem;">
<h1>✅ ¡Pago completado con éxito!</h1>
<p>Gracias por tu compra.</p>
<p id="details" style="margin-top:1rem; font-size:1.05rem;">
    Consultando detalles de tu pago...
</p>
<p style="margin-top:2rem"><a href="/" style="color:#4ade80">Volver a la tienda</a></p>

<script>
(async function () {
  const params = new URLSearchParams(location.search);
  const sid = params.get("session_id");
  if (!sid) {
    document.getElementById("details").textContent =
      "No se encontró session_id en la URL.";
    return;
  }

  try {
    const res = await fetch(`/api/payments/session/${sid}`);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      document.getElementById("details").textContent =
        `No pudimos recuperar los detalles (HTTP ${res.status}). ${text}`;
      return;
    }

    const dataText = await res.text();
    let data;
    try {
      data = JSON.parse(dataText);
    } catch (e) {
      document.getElementById("details").textContent =
        "El servidor respondió pero no envió JSON válido: " + dataText.slice(0, 200);
      return;
    }

    // Formateo monto
    const zeroDecimal = new Set([
      "BIF","CLP","DJF","GNF","JPY","KMF","KRW","MGA","PYG","RWF",
      "UGX","VND","VUV","XAF","XOF","XPF"
    ]);

    const curr = (data.currency || "CLP").toUpperCase();
    const isZero = zeroDecimal.has(curr);
    const amountRaw = data.amount_total || 0;
    const amount = isZero ? amountRaw : amountRaw / 100;

    const fmt = new Intl.NumberFormat("es-CL", {
      style: "currency",
      currency: curr,
      minimumFractionDigits: isZero ? 0 : 2,
      maximumFractionDigits: isZero ? 0 : 2
    });

    const email = data.customer_email || "-";
    const estado = (data.status || "DESCONOCIDO").toLowerCase();

    document.getElementById("details").textContent =
      `Recibimos ${fmt.format(amount)} de ${email}. `
      + `Estado: ${estado}. (ID: ${data.id})`;

  } catch (e) {
    document.getElementById("details").textContent =
      "Error consultando detalles: " + (e && e.message ? e.message : e.toString());
  }
})();
</script>

</body>
</html>
"""


# ---------------------------------
# Ruta de cancel de pago
# ---------------------------------

@app.get("/cancel", response_class=HTMLResponse)
async def cancel():
    return """
<html>
<head><title>Pago cancelado</title></head>
<body style="font-family:sans-serif; background:#111; color:#eee; padding:2rem;">
<h1>⚠️ Pago cancelado</h1>
<p>Tu sesión de pago fue cancelada o expiró.</p>
<p><a href="/" style="color:#60a5fa">Volver a la tienda</a></p>
</body>
</html>
"""


# ---------------------------------
# Archivos estáticos (CSS, imágenes)
# ---------------------------------

if os.path.isdir("./static"):
    app.mount("/static", StaticFiles(directory="./static"), name="static")


# ---------------------------------
# (Opcional futuro)
# Auto-publicador / IA background
# ---------------------------------

# Dejamos un hook vacío por ahora. Más adelante vamos
# a enchufar el auto_publisher con IA real.
# Ejemplo:
#
# async def auto_publisher():
#     while True:
#         # 1. recolectar productos candidatos (collector.py)
#         # 2. formatearlos con IA (ai_formatter.py)
#         # 3. insertarlos en DB como status="draft"
#         await asyncio.sleep(1800)
#
# @app.on_event("startup")
# async def _start_auto():
#     asyncio.create_task(auto_publisher())
