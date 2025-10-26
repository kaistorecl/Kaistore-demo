# routers/payments.py
import os
import json
import stripe
from fastapi import APIRouter, Request, HTTPException
from config import settings

from db import SessionLocal
from models import Order

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
    # Objeto de la sesión de checkout (dict)
    session_obj = obj
    sid = session_obj.get("id")

    amount_total = session_obj.get("amount_total")  # entero en centavos (salvo monedas sin decimales)
    currency = (session_obj.get("currency") or "").upper()
    customer_email = (
        (session_obj.get("customer_details") or {}).get("email")
        or session_obj.get("customer_email")
    )
    status = session_obj.get("status") or "complete"

    # Monedas sin decimales
    ZERO_DEC = {
        "BIF","CLP","DJF","GNF","JPY","KMF","KRW","MGA","PYG","RWF",
        "UGX","VND","VUV","XAF","XOF","XPF"
    }
    if amount_total is not None:
        amount_human = amount_total if currency in ZERO_DEC else (amount_total / 100.0)
    else:
        amount_human = None

    db = SessionLocal()
    try:
        # Buscar la orden que guardamos en /checkout por session_id
        order = db.query(Order).filter(Order.session_id == sid).first()
        if not order:
            # Si no existe (caso raro), la creamos
            order = Order(session_id=sid)
            db.add(order)

        order.status = status
        order.email = customer_email
        if currency:
            order.currency = currency
        if amount_human is not None:
            order.amount = float(amount_human)

        db.commit()
        print(f"✅ Orden {order.id if order.id else '-'} actualizada a {order.status} (sid={sid})")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Error actualizando orden por webhook: {e}")
        raise HTTPException(status_code=500, detail="Error actualizando orden")
    finally:
        db.close()
else:
    print("ℹ️ Evento recibido:", event_type)

    return {"received": True}
