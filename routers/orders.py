from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import stripe
import os
from config import settings

router = APIRouter(prefix="/api/orders", tags=["orders"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", settings.STRIPE_SECRET_KEY)

WEB_URL = os.getenv("WEB_URL", "https://kaistore-demo.onrender.com")  # ajuste si tu URL es distinta

class CheckoutItem(BaseModel):
    title: str
    price: float    # en la moneda indicada (CLP para esta demo)
    quantity: int = 1
    currency: str = "CLP"

class CheckoutRequest(BaseModel):
    items: list[CheckoutItem]

@router.post("/checkout")
async def create_checkout(req: CheckoutRequest):
    try:
        line_items = [
            {
                "price_data": {
                    "currency": item.currency.lower(),
                    "product_data": {"name": item.title},
                    "unit_amount": int(item.price),  # CLP sin centavos
                },
                "quantity": item.quantity,
            } for item in req.items
        ]

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            success_url=f"{WEB_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{WEB_URL}/cancel",
        )

        return {"url": session.url, "id": session.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))