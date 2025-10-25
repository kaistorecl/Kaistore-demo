import os
import json
import stripe
from fastapi import APIRouter, Request, HTTPException
from config import settings

router = APIRouter(prefix="/api/payments", tags=["payments"])

# API key de Stripe (modo prueba)
stripe.api_key = settings.STRIPE_SECRET_KEY

# Secreto de firma del webhook (lo añadiremos en Render)
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Webhook de Stripe.
    - Si STRIPE_WEBHOOK_SECRET está definido, verificamos la firma (recomendado).
    - Si no está definido, hacemos parse del JSON (sólo útil para desarrollo).
    """
    payload = (await request.body()).decode("utf-8")  # <- usar string, no bytes

    if WEBHOOK_SECRET:
        sig_header = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, WEBHOOK_SECRET
            )
        except ValueError:
            # payload inválido
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            # firma inválida
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # Fallback NO seguro (solo dev): parsear JSON sin verificar firma
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    # Obtener tipo de evento y objeto
    if isinstance(event, dict):
        event_type = event.get("type")
        obj = event.get("data", {}).get("object", {})
    else:
        event_type = event.type
        obj = event.data.object

    # Manejo básico de eventos
    if event_type == "checkout.session.completed":
        # Aquí podrías actualizar una Orden en tu DB si la tienes
        session_id = getattr(obj, "id", obj.get("id"))
        print("✅ checkout.session.completed:", session_id)
    else:
        print("➡️  Evento recibido:", event_type)

    return {"received": True}
