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

if not STRIPE_SECRET_KEY:
    # No lanzamos error al importar para no romper startup; validamos en runtime
    pass
else:
    stripe.api_key = STRIPE_SECRET_KEY


# --- Modelos ---
class CheckoutItem(BaseModel):
    title: str = Field(..., description="Nombre del producto")
    price: int = Field(..., ge=0, description="Precio en CLP, sin puntos")
    quantity: int = Field(1, ge=1)
    currency: Optional[str] = Field(None, description="Código de moneda (ej. clp)")
    image_url: Optional[str] = None

    @validator("currency", pre=True, always=True)
    def _currency_lower_or_default(cls, v):
        return (v or DEFAULT_CURRENCY).lower()


class CheckoutRequest(BaseModel):
    items: List[CheckoutItem]


# --- Endpoints ---
@router.post("/checkout")
def create_checkout_session(body: CheckoutRequest):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe no configurado (STRIPE_SECRET_KEY)")

    if not body.items:
        raise HTTPException(status_code=422, detail="Debe enviar al menos un ítem")

    line_items = []
    for it in body.items:
        # Stripe espera centavos: CLP no tiene decimales, pero igual multiplicamos por 100 (recomendado)
        unit_amount = int(it.price) * 100
        product_data = {"name": it.title}
        if it.image_url:
            product_data["images"] = [it.image_url]

        line_items.append(
            {
                "price_data": {
                    "currency": it.currency,           # <--- ya en minúsculas
                    "product_data": product_data,
                    "unit_amount": unit_amount,
                },
                "quantity": it.quantity,
            }
        )

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=f"{WEB_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{WEB_URL}/cancel",
        )
        return {"id": session.id, "url": session.url}
    except stripe.error.StripeError as e:
        # Exponemos un mensaje controlado
        raise HTTPException(status_code=400, detail=f"Stripe error: {getattr(e, 'user_message', str(e))}")
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
        raise HTTPException(status_code=400, detail=f"Stripe error: {getattr(e, 'user_message', str(e))}")
