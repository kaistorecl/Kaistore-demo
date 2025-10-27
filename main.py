import asyncio
import os
import random

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from db import Base, engine, SessionLocal
import models  # registra Product y Order en Base.metadata

from routers import orders, payments
from routers import catalog_public, admin_products

from schemas import ProductIn
from publishing import publish_product
from config import settings


# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(
    title="Kaistore API + Front",
    description="Catálogo dinámico + Checkout + Admin draft/publish",
    version="0.2.0",
)

# servir archivos estáticos (CSS, img, etc.) desde /static/*
# IMPORTANTE: necesita que exista la carpeta local ./static/
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS abierto (sandbox)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# DB init al arrancar
# -------------------------------------------------------------------
@app.on_event("startup")
def _init_db():
    Base.metadata.create_all(bind=engine)


# -------------------------------------------------------------------
# Routers existentes (API pública, admin y pagos)
# -------------------------------------------------------------------
# catálogo público: /api/products/published , /api/products/{id}
app.include_router(catalog_public.router)

# admin: /api/admin/drafts , /api/admin/auto_generate , etc.
app.include_router(admin_products.router)

# checkout / pagos Stripe
app.include_router(orders.router)
app.include_router(payments.router)


# -------------------------------------------------------------------
# Landing principal "/" = tienda reactiva en vanilla JS
# (render HTML + usa /api/products/published vía fetch)
# -------------------------------------------------------------------
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
<style>
body{
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background:#f5f5f5;
    color:#222;
    padding:0;
    margin:0;
}
.header{
    background:#fff;
    border-bottom:1px solid #ddd;
    padding:1rem;
}
.container{
    max-width:1200px;
    margin:0 auto;
    display:flex;
    align-items:center;
    gap:1rem;
}
.brand{
    display:flex;
    align-items:center;
    flex-wrap:wrap;
    gap:.5rem;
    font-size:1.2rem;
    font-weight:600;
    color:#0050d8;
}
.brand .dot{
    width:.6rem;
    height:.6rem;
    border-radius:999px;
    background:#00c853;
    display:inline-block;
}
.controls{
    flex:1;
    min-width:180px;
    display:flex;
    justify-content:flex-start;
}
.search input{
    border:1px solid #ccc;
    border-radius:4px;
    padding:.5rem .75rem;
    font-size:.9rem;
    width:100%;
    max-width:220px;
}
main.container{
    flex-direction:column;
    align-items:stretch;
    padding:1rem;
}
.grid{
    width:100%;
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
    gap:1rem;
    margin-top:1rem;
}
.card{
    background:#fff;
    border-radius:8px;
    border:1px solid #ddd;
    box-shadow:0 2px 4px rgba(0,0,0,.04);
    overflow:hidden;
    display:flex;
    flex-direction:column;
}
.card-thumb{
    background:#fafafa;
    width:100%;
    aspect-ratio:1/1;
    display:flex;
    align-items:center;
    justify-content:center;
    overflow:hidden;
}
.card-thumb img{
    width:100%;
    height:100%;
    object-fit:cover;
}
.card-body{
    padding:1rem;
    display:flex;
    flex-direction:column;
    gap:.5rem;
}
.card-title{
    font-size:1rem;
    font-weight:600;
    line-height:1.3;
    color:#111;
    margin:0;
}
.card-desc{
    font-size:.9rem;
    line-height:1.4;
    color:#444;
    margin:0;
}
.card-price{
    font-size:1rem;
    font-weight:600;
    color:#111;
}
.buy-btn{
    appearance:none;
    border:0;
    border-radius:6px;
    padding:.6rem .8rem;
    font-size:.9rem;
    font-weight:600;
    background:#0050d8;
    color:#fff;
    text-align:center;
    cursor:pointer;
}
.buy-btn:active{
    opacity:.8;
}
.footer{
    color:#666;
    font-size:.8rem;
    margin-top:2rem;
    text-align:center;
}
.toast{
    position:fixed;
    bottom:1rem;
    left:50%;
    transform:translateX(-50%);
    background:#111;
    color:#fff;
    font-size:.85rem;
    padding:.75rem 1rem;
    border-radius:6px;
    box-shadow:0 4px 16px rgba(0,0,0,.4);
    opacity:0;
    pointer-events:none;
    transition:opacity .25s ease;
    max-width:90%;
    text-align:center;
    line-height:1.4;
}
.toast.show{
    opacity:1;
}
</style>
</head>
<body>

<header class="header">
    <div class="container" style="align-items:center;">
        <div class="brand">
            <span class="dot"></span>
            <h1 style="margin:0; font-size:1.1rem; font-weight:600;">Kaistore • Demo</h1>
        </div>
        <div class="controls">
            <label class="search" style="width:100%;">
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

function toast(msg){
    $toast.textContent = msg;
    $toast.classList.add("show");
    setTimeout(()=> $toast.classList.remove("show"), 1800);
}

// CLP y monedas sin decimales
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

async function fetchProducts(){
    console.log("→ GET /api/products/published");
    const res = await fetch("/api/products/published");
    if(!res.ok){
        const txt = await res.text().catch(()=> "");
        throw new Error("No se pudieron cargar productos (HTTP " + res.status + "): " + txt);
    }
    return await res.json();
}

function render(products){
    if(!products || products.length === 0){
        $grid.innerHTML = `
        <div style="color:#777; text-align:center; grid-column:1/-1; padding:3rem 1rem;">
            No hay productos publicados todavía 👋
        </div>`;
        return;
    }

    const term = ($q.value || "").toLowerCase().trim();
    const list = term
        ? products.filter(p =>
            (p.title_marketing || "").toLowerCase().includes(term)
          )
        : products;

    if(list.length === 0){
        $grid.innerHTML = `
        <div style="color:#777; text-align:center; grid-column:1/-1; padding:3rem 1rem;">
            Sin resultados para “${term}”
        </div>`;
        return;
    }

    $grid.innerHTML = list.map(p => {
        const img = (p.image_urls && p.image_urls[0])
            ? p.image_urls[0]
            : "https://via.placeholder.com/400x400?text=Producto";

        const bullet = (p.short_bullets && p.short_bullets.length > 0)
            ? p.short_bullets[0]
            : "";

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
        </div>
        `;
    }).join("");
}

async function startCheckout(productId){
    try{
        const res = await fetch("/api/orders/checkout", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({ product_id: productId })
        });

        if(!res.ok){
            const txt = await res.text().catch(()=> "");
            console.error("checkout error", txt);
            toast("No se pudo iniciar el pago");
            return;
        }

        const data = await res.json();
        if(data && data.url){
            window.location.href = data.url;
            return;
        }

        toast("No se obtuvo URL de pago");
    }catch(e){
        console.error("checkout exception", e);
        toast("Error al iniciar pago");
    }
}

(async function init(){
    $grid.innerHTML = `<div style="color:#9aa4b2; text-align:center; padding:3rem 1rem;">
        Cargando productos…
    </div>`;

    try{
        const products = await fetchProducts();
        render(products);

        $q.addEventListener("input", () => render(products));
    }catch(e){
        console.error("init error:", e);
        $grid.innerHTML = `<div style="color:#ff8585; text-align:center; padding:3rem 1rem;">
            Error cargando productos
        </div>`;
    }
})();
</script>
</body>
</html>
"""  # noqa: E501


# -------------------------------------------------------------------
# Healthcheck para monitoreo
# -------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"ok": True}


# -------------------------------------------------------------------
# Página de éxito post-pago (Stripe redirect success_url)
# -------------------------------------------------------------------
@app.get("/success", response_class=HTMLResponse)
async def success():
    return """
<html>
<head><title>Pago completado</title></head>
<body style="font-family: sans-serif; background:#111; color:#eee; padding:2rem">
<h1 style="color:#4ade80;">✅ ¡Pago completado con éxito!</h1>
<p>Gracias por tu compra.</p>
<p id="details" style="margin-top:1rem; font-size:1.05rem;">
Consultando detalles de la orden...
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
"""  # noqa: E501


# -------------------------------------------------------------------
# Página de cancel post-pago (Stripe cancel_url)
# -------------------------------------------------------------------
@app.get("/cancel", response_class=HTMLResponse)
async def cancel():
    return """
<html><head><title>Pago cancelado</title></head>
<body style="font-family: sans-serif; background:#111; color:#eee; padding:2rem">
<h1 style="color:#ff8585;">❌ Pago cancelado</h1>
<p>Tu sesión de pago fue cancelada o expiró.</p>
<p><a href="/" style="color:#60a5fa">Volver a la tienda</a></p>
</body>
</html>
"""


# -------------------------------------------------------------------
# Autopublisher demo:
# - mete productos candidatos automáticamente en la DB, publicados,
#   usando publish_product() cada cierto rato.
# -------------------------------------------------------------------
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
        supplier_sku="AE-FOLD-BOX",
    ),
]


async def auto_publisher():
    # intenta publicar todos al inicio (pequeño delay para que la DB esté lista)
    await asyncio.sleep(2)
    with SessionLocal() as db:
        for c in CANDIDATES:
            try:
                publish_product(db, c)
            except Exception:
                # si falla uno, seguimos con los otros
                pass

    # luego cada ~30 minutos inserta uno aleatorio
    while True:
        await asyncio.sleep(1800)
        with SessionLocal() as db:
            c = random.choice(CANDIDATES)
            try:
                publish_product(db, c)
            except Exception:
                pass


@app.on_event("startup")
async def _start_task():
    asyncio.create_task(auto_publisher())
