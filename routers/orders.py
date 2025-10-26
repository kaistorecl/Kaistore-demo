# routers/orders.py

from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
import stripe

from db import SessionLocal
from models import Product
from config import settings

# Crear el router
router = APIRouter(prefix="/api/orders", tags=["orders"])

# Configurar la clave de Stripe (desde settings)
stripe.api_key = settings.STRIPE_SECRET_KEY


# ---------- Modelos ----------
class CheckoutItem(BaseModel):
    product_id: Optional[int] = None
    qty: Optional[int] = None
    title: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    currency: Optional[str] = None


class CheckoutIn(BaseModel):
    items: list[CheckoutItem]


# ---------- Helper ----------
def _get_db() -> Session:
    return SessionLocal()


# ---------- Endpoint principal ----------
@router.post("/checkout")
def checkout(payload: CheckoutIn, request: Request):
    """
    Acepta:
    {
      "items": [
        {"product_id": 3, "qty": 1}
      ]
    }
    o bien
    {
      "items": [
        {"title": "...", "price": 4990, "quantity": 1, "currency": "CLP"}
      ]
    }
    """
    db = _get_db()
    try:
        line_items = []

        for i, it in enumerate(payload.items):
            # Caso A: usando product_id
            if it.product_id is not None:
                prod = db.query(Product).filter(Product.id == it.product_id).first()
                if not prod:
                    raise HTTPException(status_code=400, detail=f"Producto {it.product_id} no existe")
                title = prod.title
                price = float(prod.price)
                quantity = it.qty or 1
                currency = settings.CURRENCY
            else:
                # Caso B: datos sueltos
                if not (it.title and it.price and it.quantity):
                    raise HTTPException(
                        status_code=422,
                        detail=f"Faltan campos en items[{i}]. Usa product_id/qty o title/price/quantity/currency",
                    )
                title = it.title
                price = float(it.price)
                quantity = int(it.quantity)
                currency = (it.currency or settings.CURRENCY).lower()

            # Stripe usa enteros (centavos)
            unit_amount = int(round(price))

            line_items.append({
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {"name": title},
                    "unit_amount": unit_amount,
                },
                "quantity": quantity,
            })

        # URLs de éxito/cancel
        origin = request.headers.get("origin") or f"https://{request.url.hostname}"
        success_url = f"{origin}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{origin}/cancel"

        # Crear sesión de pago
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
        )
# Guardar la orden en la base de datos
    from models import Order
    try:
        total_amount = sum(li["price_data"]["unit_amount"] * li["quantity"] for li in line_items)
        currency = line_items[0]["price_data"]["currency"].upper() if line_items else "CLP"

        order = Order(
            session_id=session.id,
            status="created",
            email=None,
            currency=currency,
            amount=total_amount,
        )
        db.add(order)
        db.commit()
    except Exception as e:
        print(f"⚠️ Error guardando orden: {e}")
    finally:
        db.close()

    # Respuesta esperada por el front
    return {
        "checkout_url": session.url,
        "id": session.id,
        "url": session.url,
    }
