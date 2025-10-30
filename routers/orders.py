# routers/orders.py  (v4)

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
import stripe

from db import SessionLocal
from models import Product
from settings import settings

router = APIRouter(prefix="/api/orders", tags=["orders"])

# Configura Stripe una sola vez
stripe.api_key = settings.STRIPE_SECRET_KEY

def _build_line_item_from_product(db: Session, product_id: int, qty: int = 1) -> dict:
    p = (
        db.query(Product)
        .filter(Product.id == product_id, Product.status == "published")
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado o no publicado")
    currency = (p.currency or settings.CURRENCY or "clp").lower()
    price = int(p.price)  # CLP es moneda sin decimales
    title = p.title

    return {
        "price_data": {
            "currency": currency,
            "product_data": {"name": title},
            "unit_amount": price,
        },
        "quantity": int(qty or 1),
    }

def _build_line_item_from_loose(it: dict) -> dict:
    try:
        title = str(it["title"])
        price = int(it["price"])
    except Exception:
        raise HTTPException(status_code=422, detail="items[].title y items[].price son obligatorios")

    qty = int(it.get("quantity", 1))
    currency = str(it.get("currency", settings.CURRENCY or "clp")).lower()

    return {
        "price_data": {
            "currency": currency,
            "product_data": {"name": title},
            "unit_amount": price,
        },
        "quantity": qty,
    }

@router.post("/checkout")
async def create_checkout_session(req: Request):
    # 1) Lee el JSON
    try:
        payload = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    items = payload.get("items") if isinstance(payload, dict) else None
    if not items or not isinstance(items, list):
        raise HTTPException(status_code=422, detail="items[] requerido")

    # 2) Construye line_items
    line_items = []
    with SessionLocal() as db:
        for it in items:
            if isinstance(it, dict) and "product_id" in it:
                line_items.append(
                    _build_line_item_from_product(
                        db,
                        int(it["product_id"]),
                        int(it.get("qty", 1)),
                    )
                )
            else:
                line_items.append(_build_line_item_from_loose(it))

    # 3) Crea la sesión de Stripe
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=line_items,
            success_url=f"{settings.WEB_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.WEB_URL}/cancel",
        )
    except stripe.error.StripeError as e:
        # Mensaje claro para debug
        msg = getattr(e, "user_message", None) or str(e)
        raise HTTPException(status_code=400, detail=f"Stripe: {msg}")

    # 4) Devuelve URL para redirigir desde el front
    return {"url": session.url}
