import stripe
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from db import SessionLocal
from models import Order
from config import settings

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Configura la API key de Stripe (ya la tienes en settings)
stripe.api_key = settings.STRIPE_SECRET_KEY

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook que recibe eventos de Stripe.
    Para el demo, parseamos el JSON sin verificar firma.
    (Si quieres firma, ver notas al final.)
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = data.get("type")
    obj = data.get("data", {}).get("object", {}) or {}
    metadata = obj.get("metadata", {}) or {}
    order_id = metadata.get("order_id")

    # Si no hay order_id en metadata, no podemos actualizar nada
    if not order_id:
        return {"received": True, "skipped": "no order_id in metadata", "event_type": event_type}

    # Busca la orden
    order = db.query(Order).get(int(order_id))
    if not order:
        return {"received": True, "skipped": f"order {order_id} not found", "event_type": event_type}

    # Actualiza según el evento
    if event_type == "checkout.session.completed":
        order.status = "PAID"
        db.commit()
        return {"received": True, "order_id": order_id, "status": order.status}

    if event_type in ("checkout.session.expired", "checkout.session.async_payment_failed"):
        order.status = "CANCELED"
        db.commit()
        return {"received": True, "order_id": order_id, "status": order.status}

    # Otros eventos: marcamos recibido sin cambios
    return {"received": True, "event_type": event_type, "order_id": order_id}
