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
    (async function() {
      const params = new URLSearchParams(location.search);
      const sid = params.get("session_id");
      if (!sid) {
        document.getElementById("details").textContent = "No se encontró session_id en la URL.";
        return;
      }
      try {
        const res = await fetch(`/api/payments/session/${sid}`);
        if (!res.ok) {
          document.getElementById("details").textContent = "No pudimos recuperar los detalles del pago.";
          return;
        }
        const data = await res.json();
        // Algunas monedas no usan decimales (CLP, JPY, KRW, etc.)
const zeroDecimal = new Set([
  "BIF","CLP","DJF","GNF","JPY","KMF","KRW","MGA","PYG","RWF",
  "UGX","VND","VUV","XAF","XOF","XPF"
]);

let amount = data.amount_total || 0;
const curr = (data.currency || "CLP").toUpperCase();
const isZero = zeroDecimal.has(curr);

// Si no tiene decimales NO dividimos entre 100
const monto = isZero ? amount : amount / 100;

// Formato bonito
const fmt = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: curr,
  minimumFractionDigits: isZero ? 0 : 2,
  maximumFractionDigits: isZero ? 0 : 2
});

document.getElementById("details").textContent =
  `Recibimos ${fmt.format(monto)} de ${email}. ` +
  `Estado: ${estado}. (ID: ${data.id})`;
        const moneda = (data.currency || "CLP").toUpperCase();
        const email = data.customer_email || "cliente";
        const estado = data.status || "DESCONOCIDO";
        document.getElementById("details").textContent =
          `Recibimos ${monto} ${moneda} de ${email}. Estado: ${estado}. (ID: ${data.id})`;
      } catch (e) {
        document.getElementById("details").textContent = "Error consultando detalles.";
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


# ----- Servir export estático de Next.js (si existe ./static) -----
if os.path.isdir("./static"):
    app.mount("/", StaticFiles(directory="./static", html=True), name="static")


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
