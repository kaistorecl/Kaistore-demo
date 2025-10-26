import asyncio
import os
import random
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session

# DB y modelos
from db import Base, engine, SessionLocal
import models  # importa Product, registra tablas en Base.metadata

# Routers existentes (pagos / órdenes)
from routers import orders, payments

# Routers nuevos (catálogo público y panel admin)
from routers import products, admin_products

# Extras que ya usabas en tu app original para autopublisher
from schemas import ProductIn
from publishing import publish_product
from config import settings


# -------------------------------------------------
# Inicializar FastAPI
# -------------------------------------------------
app = FastAPI(
    title="Kaistore API + Front",
    description="Catálogo dinámico + Checkout + Admin draft/publish",
    version="0.2.0",
)

# -------------------------------------------------
# CORS (abierto mientras desarrollas)
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego puedes cerrar esto a tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Crear tablas si no existen al iniciar
# -------------------------------------------------
@app.on_event("startup")
def _init_db():
    Base.metadata.create_all(bind=engine)

# -------------------------------------------------
# Montar routers API
# -------------------------------------------------
# catálogo público
app.include_router(products.router)

# admin (ver drafts y publicar)
app.include_router(admin_products.router)

# tus routers anteriores de órdenes y pagos
app.include_router(orders.router)
app.include_router(payments.router)


# -------------------------------------------------
# Página principal / tienda
# Hace fetch a /api/products/published y renderiza tarjetas
# -------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Kaistore • Demo</title>
    <link rel="stylesheet" href="/static/style.css"/>
</head>
<body>
<header class="header">
    <div class="container" style="display:flex; align-items:center;">
        <div class="brand">
            <span class="dot"></span>
            <h1>Kaistore • Demo</h1>
        </div>
        <div class="controls">
            <label class="search">
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
// refs
const $grid  = document.getElementById("grid");
const $q     = document.getElementById("q");
const $toast = document.getElementById("toast");

// toast helper
function toast(msg){
    $toast.textContent = msg;
    $toast.classList.add("show");
    setTimeout(()=> $toast.classList.remove("show"), 1800);
}

// formatear moneda (maneja CLP sin decimales)
function formatPrice(amount, currency){
    const zeroDecimal = new Set([
        "BIF","CLP","DJF","GNF","JPY","KMF","KRW","MGA","PYG","RWF",
        "UGX","VND","VUV","XAF","XOF","XPF"
    ]);

    const curr = (currency || "CLP").toUpperCase();
    const isZero = zeroDecimal.has(curr);
    const raw = amount || 0;
    const value = isZero ? raw : raw / 100;

    const fmt = new Intl.NumberFormat("es-CL", {
        style: "currency",
        currency: curr,
        minimumFractionDigits: isZero ? 0 : 2,
        maximumFractionDigits: isZero ? 0 : 2,
    });

    return fmt.format(value);
}

// pide catálogo público
async function fetchProducts(){
    const res = await fetch("/api/products/published");
    if(!res.ok){
        const txt = await res.text().catch(()=> "");
        throw new Error("No se pudieron cargar productos: " + txt);
    }
    return await res.json();
}

// render cards en grid
function render(products){
    if(!products || products.length === 0){
        $grid.innerHTML = `
            <div style="color:#999; text-align:center; padding:3rem 1rem;">
                <p>No hay productos publicados todavía 🙌</p>
            </div>`;
        return;
    }

    const term = ($q.value || "").toLowerCase().trim();
    const list = term
        ? products.filter(p =>
            (p.title_marketing || "").toLowerCase().includes(term) ||
            (p.short_bullets || []).join(" ").toLowerCase().includes(term)
          )
        : products;

    if(list.length === 0){
        $grid.innerHTML = `
            <div style="color:#999; text-align:center; padding:3rem 1rem;">
                <p>Sin coincidencias para "<b>${term}</b>"</p>
            </div>`;
        return;
    }

    $grid.innerHTML = list.map(p => {
        const img = (p.image_urls && p.image_urls.length > 0)
          ? p.image_urls[0]
          : "https://via.placeholder.com/600x600?text=Producto";

        const bullet = (p.short_bullets && p.short_bullets.length > 0)
          ? p.short_bullets[0]
          : "Descubre este producto.";

        const priceText = formatPrice(p.price, p.currency);

        return `
        <div class="card">
            <div class="card-thumb">
                <img src="${img}" alt="${p.title_marketing || "Producto"}"/>
            </div>
            <div class="card-body">
                <h2 class="card-title">${p.title_marketing || "Producto"}</h2>
                <p class="card-desc">${bullet}</p>
                <div class="card-price">${priceText}</div>
                <button class="buy-btn" onclick="startCheckout(${p.id})">
                    Comprar ahora
                </button>
            </div>
        </div>`;
    }).join("");
}

// iniciar checkout
async function startCheckout(productId){
    try{
        const res = await fetch("/api/payments/create", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ product_id: productId })
        });

        if(!res.ok){
            const t = await res.text().catch(()=> "");
            console.error("checkout error:", t);
            toast("No se pudo iniciar el pago");
            return;
        }

        const data = await res.json();
        if(data && data.url){
            window.location.href = data.url;
        }else{
            toast("No se pudo iniciar el pago");
        }
    }catch(e){
        console.error("checkout err:", e);
        toast("No se pudo iniciar el pago");
    }
}

// init page
(async function init(){
    $grid.innerHTML = `<div style="color:#9aa4b2; text-align:center; padding:3rem 1rem;">
        Cargando catálogo…
    </div>`;
    try{
        const products = await fetchProducts();
        render(products);
        $q.addEventListener("input", () => render(products));
    }catch(e){
        console.error("init error:", e);
        $grid.innerHTML = `<div style="color:#ff5855; text-align:center; padding:3rem 1rem;">
            <p>Error cargando catálogo 😭</p>
        </div>`;
    }
})();
</script>
</body>
</html>
"""


# -------------------------------------------------
# Healthcheck
# -------------------------------------------------
@app.get("/api/health")
async def health():
    return {"ok": True}


# -------------------------------------------------
# Página de éxito de pago (Stripe)
# -------------------------------------------------
@app.get("/success", response_class=HTMLResponse)
async def success():
    return """
<html>
<head><title>Pago completado</title></head>
<body style="font-family: sans-serif; background:#111; color:#eee; padding:2rem">
<h1 style="color:#4ade80;">✅ Pago completado con éxito!</h1>
<p>Gracias por tu compra.</p>
<p id="details" style="margin-top:1rem; font-size:1.05rem;">Consultando detalles...</p>
<p style="margin-top:2rem"><a href="/" style="color:#4ade80">volver a la tienda</a></p>

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

        const dataText = await res.text();
        let data;
        try {
            data = JSON.parse(dataText);
        } catch (e) {
            document.getElementById("details").textContent =
                "El servidor respondió pero no envió JSON válido: " + dataText.slice(0, 200);
            return;
        }

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
            "Error consultando detalles: " + (e && (e.message || e.toString()));
    }
})();
</script>
</body>
</html>
"""


# -------------------------------------------------
# Página de cancel de pago
# -------------------------------------------------
@app.get("/cancel", response_class=HTMLResponse)
async def cancel():
    return """
<html>
<head><title>Pago cancelado</title></head>
<body style="font-family: sans-serif; background:#111; color:#eee; padding:2rem">
<h1 style="color:#ff5855;">❌ Pago cancelado</h1>
<p>Tu sesión de pago fue cancelada o expiró.</p>
<p><a href="/" style="color:#60a5fa">Volver a la tienda</a></p>
</body>
</html>
"""


# -------------------------------------------------
# Servir /static (tu CSS, imágenes, etc.)
# -------------------------------------------------
if os.path.isdir("./static"):
    app.mount("/static", StaticFiles(directory="./static"), name="static")


# -------------------------------------------------
# Auto publisher en background
# Sigue tu idea: mete candidatos y los publica de a poco
# publish_product(db, ProductIn(...))
# -------------------------------------------------
CANDIDATES = [
    ProductIn(
        title="Llave ahorradora de agua 360°",
        description="Cabezal giratorio que reduce consumo de agua hasta 30% y facilita limpieza de lavaplatos.",
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
        supplier_sku="ORG-FOLD-01",
    ),
]


async def auto_publisher():
    # Primer batch al arrancar
    await asyncio.sleep(2)
    with SessionLocal() as db:
        for c in CANDIDATES:
            try:
                publish_product(db, c)
            except Exception:
                pass

    # Publicar uno random cada 30 min
    while True:
        await asyncio.sleep(1800)
        with SessionLocal() as db:
            c = random.choice(CANDIDATES)
            try:
                publish_product(db, c)
            except Exception:
                pass


@app.on_event("startup")
async def _start_auto_task():
    asyncio.create_task(auto_publisher())
