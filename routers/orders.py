# routers/orders.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import os
import stripe

router = APIRouter(prefix="/api/orders", tags=["orders"])

# --- Config ---
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
WEB_URL = os.getenv("WEB_URL", "http://localhost:8000").rstrip("/")
DEFAULT_CURRENCY = os.getenv("CURRENCY", "clp").lower()

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Monedas sin decimales (no multiplicar por 100)
ZERO_DECIMAL = {
    "bif","clp","djf","gnf","jpy","kmf","krw","mga","pyg","rwf","vnd","vuv","xaf","xof","xpf"
}

class CheckoutItem(BaseModel):
    title: str = Field(..., description="Nombre del producto")
    price: int = Field(..., ge=0, description="Precio en moneda entera (CLP)")
    quantity: int = Field(1, ge=1)
    currency: Optional[str] = Field(None, description="Código de moneda (clp, usd, etc.)")
    image_url: Optional[str] = None

    @validator("currency", pre=True, always=True)
    def _currency_lower_or_default(cls, v):
        return (v or DEFAULT_CURRENCY).lower()

class CheckoutRequest(BaseModel):
    items: List[CheckoutItem]

@router.post("/checkout")
def create_checkout_session(body: CheckoutRequest):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe no configurado (STRIPE_SECRET_KEY)")

    if not body.items:
        raise HTTPException(status_code=422, detail="Debe enviar al menos un ítem")

    line_items = []
    for it in body.items:
        # Para monedas zero-decimal (p.ej., CLP) NO multiplicamos por 100
        unit_amount = int(it.price)
        if it.currency not in ZERO_DECIMAL:
            unit_amount = unit_amount * 100

        product_data = {"name": it.title}
        if it.image_url:
            product_data["images"] = [it.image_url]

        line_items.append({
            "price_data": {
                "currency": it.currency,
                "product_data": product_data,
                "unit_amount": unit_amount,
            },
            "quantity": it.quantity,
        })

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=f"{WEB_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{WEB_URL}/cancel",
        )
        return {"id": session.id, "url": session.url}
    except stripe.error.StripeError as e:
        # Mensaje claro hacia el front
        user_msg = getattr(e, "user_message", None) or getattr(e, "code", None) or str(e)
        raise HTTPException(status_code=400, detail=f"Stripe error: {user_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando checkout: {str(e)}")

@router.get("/{session_id}")
def get_order(session_id: str):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe no configurado (STRIPE_SECRET_KEY)")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": session.id,
            "payment_status": session.get("payment_status"),
            "status": session.get("status"),
            "amount_total": session.get("amount_total"),
            "currency": session.get("currency"),
        }
    except stripe.error.StripeError as e:
        user_msg = getattr(e, "user_message", None) or getattr(e, "code", None) or str(e)
        raise HTTPException(status_code=400, detail=f"Stripe error: {user_msg}")
