import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import SessionLocal
from models import Product
from config import settings

router = APIRouter(prefix="/api/orders", tags=["orders"])

stripe.api_key = settings.STRIPE_SECRET_KEY

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/checkout")
def checkout(payload: dict, db: Session = Depends(get_db)):
    items = payload.get("items", [])
    email = payload.get("customer_email")
    if not items or not email:
        raise HTTPException(status_code=400, detail="items and customer_email required")

    line_items = []
    for it in items:
        p = db.query(Product).get(it["product_id"])
        if not p:
            raise HTTPException(status_code=404, detail=f"Product {it['product_id']} not found")
        qty = int(it.get("qty", 1))
        line_items.append({
            "price_data": {
                "currency": settings.CURRENCY.lower(),   # CLP en entero
                "product_data": {"name": p.title},
                "unit_amount": int(p.price)
            },
            "quantity": qty
        })

    session = stripe.checkout.Session.create(
        mode="payment",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
        customer_email=email,
        line_items=line_items
    )
    return {"checkout_url": session.url}
