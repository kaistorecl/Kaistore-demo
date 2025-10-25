from fastapi import APIRouter, Request, HTTPException
import stripe
import os
from config import settings

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Clave de Stripe (test) desde env
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", settings.STRIPE_SECRET_KEY)
# Secreto de firma del webhook (lo copiaremos de Stripe al crear el endpoint)
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            # Si aún no definiste STRIPE_WEBHOOK_SECRET, acepta sin verificar firma (solo para pruebas iniciales)
            event = stripe.Event.construct_from(stripe.util.json.loads(payload), stripe.api_key)
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        print("✅ checkout.session.completed:", data.get("id"))
    elif event_type == "payment_intent.succeeded":
        print("✅ payment_intent.succeeded:", data.get("id"))
    else:
        print("ℹ️ Evento no manejado:", event_type)

    return {"received": True}