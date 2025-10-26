# routers/orders.py

from fastapi import APIRouter, Request, HTTPException
import stripe
from config import settings
from db import SessionLocal
from models import Order

router = APIRouter(prefix="/api/orders", tags=["orders"])

stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/checkout")
async def create_checkout_session(request: Request):
    """
    Crea una sesión de Checkout en Stripe y guarda la orden en la base de datos.
    """
    try:
        body = await request.json()
        items = body.get("items", [])

        if not items:
            raise HTTPException(status_code=400, detail="No se enviaron productos")

        db = SessionLocal()
        line_items = []

        # Procesar productos
        for i, it in enumerate(items):
            if not (it.get("title") and it.get("price") and it.get("quantity")):
                raise HTTPException(status_code=422, detail=f"Faltan campos en item {i}")

            title = it["title"]
            price = float(it["price"])
            quantity = int(it["quantity"])
            currency = (it.get("currency") or settings.CURRENCY).lower()

            unit_amount = int(round(price * 100))  # Stripe usa centavos

            line_items.append({
                "price_data": {
                    "currency": currency,
                    "product_data": {"name": title},
                    "unit_amount": unit_amount,
                },
                "quantity": quantity,
            })

        # URLs de retorno
        origin = request.headers.get("origin") or f"https://{request.url.hostname}"
        success_url = f"{origin}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{origin}/cancel"

        # Crear sesión de pago
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        # Guardar orden en DB
        try:
            total_amount = sum(li["price_data"]["unit_amount"] * li["quantity"] for li in line_items)
            currency = line_items[0]["price_data"]["currency"].upper() if line_items else "CLP"

            order = Order(
                session_id=session.id,
                status="created",
                email=None,
                currency=currency,
                amount=total_amount,
            )
            db.add(order)
            db.commit()
        except Exception as e:
            print(f"⚠️ Error guardando orden: {e}")
        finally:
            db.close()

        return {
            "checkout_url": session.url,
            "id": session.id,
            "url": session.url,
        }

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando checkout: {e}")


@router.get("/{session_id}")
async def get_order(session_id: str):
    """
    Retorna los detalles de una orden guardada por session_id.
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.session_id == session_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")

        return {
            "session_id": order.session_id,
            "status": order.status,
            "amount": order.amount,
            "currency": order.currency,
            "email": order.email,
            "created_at": order.created_at,
        }
    finally:
        db.close()
