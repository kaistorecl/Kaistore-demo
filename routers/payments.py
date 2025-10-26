# routers/payments.py
import os
import json
import stripe
from fastapi import APIRouter, Request, HTTPException
from config import settings

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Clave secreta de Stripe (modo prueba)
stripe.api_key = settings.STRIPE_SECRET_KEY

# (Opcional) Secreto de firma del webhook: ponlo en Render como STRIPE_WEBHOOK_SECRET
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.get("/session/{session_id}")
def get_session_details(session_id: str):
    """
    Devuelve detalles de la sesión de Checkout para mostrar en /success
    """
    try:
        # expand line_items para obtener info de los productos si quieres
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["line_items", "payment_intent"]
        )

        # Campos útiles para el front
        data = {
            "id": session.id,
            "status": session.status,
            "amount_total": session.amount_total,   # centavos
            "currency": (session.currency or "").upper(),
            "customer_email": session.get("customer_details", {}).get("email"),
        }

        # (Opcional) algunos extras
        if session.line_items and session.line_items.data:
            items = []
            for li in session.line_items.data:
                items.append({
                    "description": li.description,
                    "quantity": li.quantity,
                    "amount_subtotal": li.amount_subtotal,
                    "amount_total": li.amount_total,
                    "currency": (li.currency or "").upper(),
                })
            data["items"] = items

        if session.payment_intent:
            pi = session.payment_intent
            data["payment_intent_status"] = getattr(pi, "status", None)

        return data

    except stripe.error.InvalidRequestError as e:
        # por ejemplo: ID no existe o es inválido
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error consultando sesión de pago")

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Webhook de Stripe (opcional pero recomendable).
    Si configuras STRIPE_WEBHOOK_SECRET, verificamos la firma.
    """
    payload = await request.body()

    # Verificación de firma si hay secreto configurado
    if WEBHOOK_SECRET:
        sig_header = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # Fallback para desarrollo sin verificar firma
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    # Manejo básico
    if isinstance(event, dict):
        event_type = event.get("type")
        obj = event.get("data", {}).get("object", {})
    else:
        event_type = event.type
        obj = event.data.object

    if event_type == "checkout.session.completed":
        # Aquí podrías actualizar tu DB con el estado de la orden
        print("✅ checkout.session.completed:", getattr(obj, "id", obj.get("id")))
    else:
        print("ℹ️ Evento:", event_type)

    return {"received": True}
