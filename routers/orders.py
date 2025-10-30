# routers/orders.py  (v4.1)

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
import os, stripe

from db import SessionLocal
from models import Product

# ---- Carga settings desde config.py o desde variables de entorno ----
try:
    from config import settings  # <— tu proyecto tiene config.py
    STRIPE_SECRET_KEY = settings.STRIPE_SECRET_KEY
    WEB_URL = settings.WEB_URL
    DEFAULT_CURRENCY = (getattr(settings, "CURRENCY", "clp") or "clp").lower()
except Exception:
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    WEB_URL = os.getenv("WEB_URL", "http://localhost:8000")
    DEFAULT_CURRENCY = (os.getenv("CURRENCY", "clp") or "clp").lower()

router = APIRouter(prefix="/api/orders", tags=["orders"])
stripe.api_key = STRIPE_SECRET_KEY

def _cur(value):  # normaliza moneda
    return (value or DEFAULT_CURRENCY).lower()

def _li_from_product(db: Session, product_id: int, qty: int = 1) -> dict:
    p = (
        db.query(Product)
        .filter(Product.id == product_id, Product.status == "published")
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado o no publicado")
    return {
        "price_data": {
            "currency": _cur(getattr(p, "currency", DEFAULT_CURRENCY)),
            "product_data": {"name": p.title},
            "unit_amount": int(p.price),  # CLP sin decimales
        },
        "quantity": int(qty or 1),
    }

def _li_from_loose(it: dict) -> dict:
    if not isinstance(it, dict):
        raise HTTPException(status_code=422, detail="items[] debe ser objeto")
    if "title" not in it or "price" not in it:
        raise HTTPException(status_code=422, detail="items[].title y items[].price son obligatorios")
    return {
        "price_data": {
            "currency": _cur(it.get("currency")),
            "product_data": {"name": str(it["title"])},
            "unit_amount": int(it["price"]),
        },
        "quantity": int(it.get("quantity", 1)),
    }

@router.post("/checkout")
async def checkout(req: Request):
    # 1) leer body
    try:
        payload = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    items = payload.get("items") if isinstance(payload, dict) else None
    if not items or not isinstance(items, list):
        raise HTTPException(status_code=422, detail="items[] requerido")

    # 2) construir line_items
    line_items = []
    with SessionLocal() as db:
        for it in items:
            if isinstance(it, dict) and "product_id" in it:
                line_items.append(_li_from_product(db, int(it["product_id"]), int(it.get("qty", 1))))
            else:
                line_items.append(_li_from_loose(it))

    # 3) crear sesión de Stripe
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=line_items,
            success_url=f"{WEB_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{WEB_URL}/cancel",
        )
    except stripe.error.StripeError as e:
        msg = getattr(e, "user_message", None) or str(e)
        raise HTTPException(status_code=400, detail=f"Stripe: {msg}")

    # 4) devolver URL para redirección
    return {"url": session.url}
