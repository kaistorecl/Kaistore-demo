import asyncio, os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from db import Base, engine, SessionLocal
from models import *  # noqa
from routers import products, orders, payments
from schemas import ProductIn
from publishing import publish_product
from config import settings

app = FastAPI(title="Kaistore API + Front")

# DB
Base.metadata.create_all(bind=engine)

# Routers API
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)

@app.get("/api/health")
async def health():
    return {"ok": True}

# Serve static Next.js export (will be built to ./static)
if os.path.isdir("./static"):
    app.mount("/", StaticFiles(directory="./static", html=True), name="static")

# Background demo: auto publish candidates periodically
CANDIDATES = [
  ProductIn(
    title="Llave ahorradora de agua 360°",
    description="Cabezal giratorio que reduce consumo de agua hasta 30% y facilita limpieza.",
    image_url="https://picsum.photos/seed/water/800/800",
    price=5990.0, currency=settings.CURRENCY, score=88, supplier_sku="AE-360-WATER"
  ),
  ProductIn(
    title="Cepillo eléctrico multiuso para cocina",
    description="Elimina grasa rápidamente; recargable USB; 3 cabezales.",
    image_url="https://picsum.photos/seed/brush/800/800",
    price=8490.0, currency=settings.CURRENCY, score=83, supplier_sku="AE-BRUSH-USB"
  ),
  ProductIn(
    title="Organizador plegable para ropa",
    description="Orden instantáneo, ahorra espacio y mantiene tus prendas visibles.",
    image_url="https://picsum.photos/seed/organizer/800/800",
    price=4990.0, currency=settings.CURRENCY, score=79
  )
]

async def auto_publisher():
    # publish one candidate on startup
    await asyncio.sleep(2)
    with SessionLocal() as db:
        for c in CANDIDATES:
            try:
                publish_product(db, c)
            except Exception:
                pass
    # then periodically (every 30 min) publish one random
    import random, time
    while True:
        with SessionLocal() as db:
            c = random.choice(CANDIDATES)
            try:
                publish_product(db, c)
            except Exception:
                pass
        await asyncio.sleep(1800)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(auto_publisher())
