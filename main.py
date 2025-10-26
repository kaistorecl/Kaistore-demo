import asyncio
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from db import Base, engine, SessionLocal
from models import *  # noqa
from routers import products, orders, payments
from schemas import ProductIn
from publishing import publish_product
from config import settings

app = FastAPI(title="Kaistore API + Front")

# ----- DB init en startup -----
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# ----- Routers API -----
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Kaistore — Demo</title>
  <link rel="stylesheet" href="/static/style.css"/>
</head>
<body>
  <header class="header">
    <div class="container" style="display:flex; align-items:center;">
      <div class="brand">
        <span class="dot"></span>
        <h1>Kaistore — Demo</h1>
      </div>
      <div class="controls">
        <label class="search">
          🔎
          <input id="q" placeholder="Buscar productos…"/>
        </label>
      </div>
    </div>
  </header>

  <main class="container">
    <div id="grid" class="grid"></div>
    <p class="footer">Sandbox • Pagos de prueba en Stripe</p>
  </main>

  <div id="toast" class="toast"></div>

<script>
const $grid = document.getElementById("grid");
const $q = document.getElementById("q");
const $toast = document.getElementById("toast");

const CLP = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });

function toast(msg){
  $toast.textContent = msg;
  $toast.classList.add("show");
  setTimeout(()=> $toast.classList.remove("show"), 1800);
}

async function fetchProducts(){
  const res = await fetch("/api/products");
  if(!res.ok){ throw new Error("No se pudieron cargar productos"); }
  return await res.json();
}

function render(products){
  const term = ($q.value || "").toLowerCase().trim();
  const list = term ? products.filter(p =>
      p.title.toLowerCase().includes(term) || (p.description||"").toLowerCase().includes(term)
    ) : products;

  $grid.innerHTML = list.map(p => `
    <article class="card">
      <img class="img" src="${p.image_url}" alt="${p.title}"/>
      <div class="body">
        <div class="row">
          <div class="badge">${(p.supplier_sku || "SKU")}</div>
          <div class="price">${CLP.format(p.price || 0)}</div>
        </div>
        <div class="title">${p.title}</div>
        <div class="desc">${p.description || ""}</div>
        <div class="row">
          <button class="btn" onclick='buy(${p.id})'>Comprar</button>
        </div>
      </div>
    </article>
  `).join("");
}

async function buy(productId){
  try{
    const body = { items: [{ product_id: productId, qty: 1 }] };
    const res = await fetch("/api/orders/checkout", {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(body)
    });
    if(!res.ok){
      const txt = await res.text().catch(()=> "");
      throw new Error(\`Error creando checkout (HTTP \${res.status}): \${txt}\`);
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

(async function init(){
  try{
    const products = await fetchProducts();
    render(products);
    $q.addEventListener("input", () => render(products));
  }catch(e){
    $grid.innerHTML = `<div style="color:#ff8585">Error: ${e.message}</div>`;
  }
})();
</script>
</body>
</html>
"""
@app.get("/api/health")
async def health():
    return {"ok": True}

# ====== (NUEVO) Rutas de confirmación/cancelación ANTES de montar estáticos ======
@app.get("/success", response_class=HTMLResponse)
async def success():
    return """
<html>
<head><title>Pago completado</title></head>
<body style="font-family: sans-serif; background:#111; color:#eee; padding:2rem">
  <h1>✅ ¡Pago completado con éxito!</h1>
  <p>Gracias por tu compra.</p>
  <p id="details" style="margin-top:1rem; font-size:1.05rem;">Consultando detalles de tu pago...</p>
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
        `No pudimos recuperar los detalles (HTTP ${res.status}). ${text || ""}`.trim();
      return;
    }

    // Parseo seguro
    const dataText = await res.text();
    let data;
    try {
      data = JSON.parse(dataText);
    } catch (e) {
      document.getElementById("details").textContent =
        "El servidor respondió pero no envió JSON válido: " + dataText.slice(0, 200);
      return;
    }

    // Monedas sin decimales (CLP, etc.)
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

    const email = data.customer_email || "—";
    const estado = (data.status || "DESCONOCIDO").toLowerCase();

    document.getElementById("details").textContent =
      `Recibimos ${fmt.format(amount)} de ${email}. ` +
      `Estado: ${estado}. (ID: ${data.id})`;

  } catch (e) {
    document.getElementById("details").textContent =
      "Error consultando detalles: " + (e && (e.message || e.toString()));
  }
})();
</script>
</body>
</html>
"""

@app.get("/cancel", response_class=HTMLResponse)
async def cancel():
    return """
<html>
  <head><title>Pago cancelado</title></head>
  <body style="font-family: sans-serif; background:#111; color:#eee; padding:2rem">
    <h1>⚠️ Pago cancelado</h1>
    <p>Tu sesión de pago fue cancelada o expiró.</p>
    <p><a href="/" style="color:#60a5fa">Volver a la tienda</a></p>
  </body>
</html>
"""  # noqa: E501
# ================================================================================



# --- Servir archivos estáticos (CSS, imágenes, etc.) ---
if os.path.isdir("./static"):
    app.mount("/static", StaticFiles(directory="./static"), name="static")

# ----- Demo de “auto publicación” en background -----
CANDIDATES = [
    ProductIn(
        title="Llave ahorradora de agua 360°",
        description="Cabezal giratorio que reduce consumo de agua hasta 30% y facilita limpieza.",
        image_url="https://picsum.photos/seed/water/800/800",
        price=5990.0,
        currency=settings.CURRENCY,
        score=88,
        supplier_sku="AE-360-WATER",
    ),
    ProductIn(
        title="Cepillo eléctrico multiuso para cocina",
        description="Elimina grasa rápidamente; recargable USB; 3 cabezales.",
        image_url="https://picsum.photos/seed/brush/800/800",
        price=8490.0,
        currency=settings.CURRENCY,
        score=83,
        supplier_sku="AE-BRUSH-USB",
    ),
    ProductIn(
        title="Organizador plegable para ropa",
        description="Orden instantáneo, ahorra espacio y mantiene tus prendas visibles.",
        image_url="https://picsum.photos/seed/organizer/800/800",
        price=4990.0,
        currency=settings.CURRENCY,
        score=79,
    ),
]

async def auto_publisher():
    # Publica uno al arrancar
    await asyncio.sleep(2)
    with SessionLocal() as db:
        for c in CANDIDATES:
            try:
                publish_product(db, c)
            except Exception:
                pass

    # Luego publica uno aleatorio cada 30 min
    import random
    while True:
        with SessionLocal() as db:
            c = random.choice(CANDIDATES)
            try:
                publish_product(db, c)
            except Exception:
                pass
        await asyncio.sleep(1800)


@app.on_event("startup")
async def _start_task():
    asyncio.create_task(auto_publisher())
