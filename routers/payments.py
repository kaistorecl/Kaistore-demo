import os
import json
import stripe
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session

from config import settings
from db import SessionLocal
from models import CheckoutSession

router = APIRouter(prefix="/api/payments", tags=["payments"])

# API key de Stripe (modo prueba)
stripe.api_key = settings.STRIPE_SECRET_KEY

# Clave de firma del webhook (configurada en Stripe → Workbench → Webhooks)
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Webhook de Stripe.
    - Si STRIPE_WEBHOOK_SECRET está definido, verificamos la firma (recomendado).
    - Si no, parseamos el JSON (útil en desarrollo).
    """
    payload = await request.body()

    if WEBHOOK_SECRET:
        sig_header = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # fallback sin firma (dev)
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    # Normalizamos para acceder a tipo y objeto
    if isinstance(event, dict):
        event_type = event.get("type")
        obj = event.get("data", {}).get("object", {}) or {}
    else:
        event_type = event.type
        obj = event.data.object

    session_id = obj.get("id")

    # Abrimos DB
    db: Session = SessionLocal()

    try:
        if event_type == "checkout.session.completed":
            cs = db.get(CheckoutSession, session_id) if session_id else None
            if not cs and session_id:
                cs = CheckoutSession(id=session_id)

            # Campos útiles
            amount_total = obj.get("amount_total") or 0
            currency = obj.get("currency") or settings.CURRENCY
            email = (obj.get("customer_details") or {}).get("email") or obj.get("customer_email")

            if not cs and session_id:
                cs = CheckoutSession(
                    id=session_id,
                    amount_total=amount_total,
                    currency=currency,
                    customer_email=email,
                    status="PAID",
                )
                db.add(cs)
            else:
                # upsert / update
                if cs:
                    cs.amount_total = amount_total
                    cs.currency = currency
                    cs.customer_email = email
                    cs.status = "PAID"

            db.commit()
            return {"received": True, "session": session_id, "status": "PAID"}

        elif event_type in ("checkout.session.expired",):
            if session_id:
                cs = db.get(CheckoutSession, session_id)
                if cs:
                    cs.status = "EXPIRED"
                    db.commit()
            return {"received": True, "session": session_id, "status": "EXPIRED"}

        else:
            # otros eventos: marcamos recibido
            return {"received": True, "event_type": event_type, "session": session_id}
    finally:
        db.close()


@router.get("/session/{session_id}")
def get_session(session_id: str):
    """Consultar detalles guardados de una sesión de Checkout."""
    db: Session = SessionLocal()
    try:
        cs = db.get(CheckoutSession, session_id)
        if not cs:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": cs.id,
            "amount_total": cs.amount_total,
            "currency": cs.currency,
            "customer_email": cs.customer_email,
            "status": cs.status,
            "created_at": cs.created_at.isoformat(),
        }
    finally:
        db.close()
