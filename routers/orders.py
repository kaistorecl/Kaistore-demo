# routers/orders.py

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
import stripe

from db import SessionLocal
from models import Product, Order
from config import settings

router = APIRouter(prefix="/api/orders", tags=["orders"])

# Clave Stripe (desde settings)
stripe.api_key = settings.STRIPE_SECRET_KEY

# Monedas sin decimales en Stripe
ZERO_DEC = {
    "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF",
    "UGX", "VND", "VUV", "XAF", "XOF", "XPF"
}

# ------------ Helper ------------
def _get_db() -> Session:
    return SessionLocal()

def _price_to_unit_amount(price: float, currency: str) -> int:
    """
    Convierte un precio humano a unit_amount para Stripe.
    - Monedas sin decimales: se usa el valor tal cual (4990 CLP -> 4990).
    - Con decimales: se multiplica por 100 (49.90 USD -> 4990).
    """
    curr = (currency or "").upper()
    if curr in ZERO_DEC:
        return int(round(price))
    return int(round(price * 100))


# ----------- Endpoint principal -----------
@router.post("/checkout")
async def create_checkout_session(request: Request):
    """
    Acepta items en dos formatos:

    1) Por product_id:
      {"items":[ {"product_id": 3, "qty": 1} ]}

    2) Datos sueltos:
      {"items":[ {"title":"...", "price":4990, "quantity":1, "currency":"CLP"} ]}
    """
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    items: List[Dict[str, Any]] = body.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="No se enviaron productos")

    db = _get_db()
    line_items: List[Dict[str, Any]] = []

    try:
        for i, it in enumerate(items):
            title: str
            price: float
            quantity: int
            currency: str

            # Caso A: viene product_id (+ qty opcional)
            if "product_id" in it:
                prod_id = it.get("product_id")
                if prod_id is None:
                    raise HTTPException(status_code=422, detail=f"Falta product_id en item {i}")

                prod = db.query(Product).filter(Product.id == prod_id).first()
                if not prod:
                    raise HTTPException(status_code=400, detail=f"Producto {prod_id} no existe")

                title = prod.title
                price = float(prod.price)
                quantity = int(it.get("qty", 1))
                currency = settings.CURRENCY

            # Caso B: datos sueltos
            else:
                if not (it.get("title") and it.get("price") and it.get("quantity")):
                    raise HTTPException(status_code=422, detail=f"Faltan campos en item {i}")

                title = str(it["title"])
                price = float(it["price"])
                quantity = int(it["quantity"])
                currency = str(it.get("currency") or settings.CURRENCY)

            unit_amount = _price_to_unit_amount(price, currency)

            line_items.append({
                "price_data": {
                    "currency": currency.lower(),
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

        # Guardar orden básica en DB
        try:
            total_amount = sum(li["price_data"]["unit_amount"] * li["quantity"] for li in line_items)
            currency = line_items[0]["price_data"]["currency"].upper() if line_items else settings.CURRENCY

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
            # No interrumpimos el return del checkout; igual devolvemos la URL

        return {
            "checkout_url": session.url,
            "id": session.id,
            "url": session.url,
        }

    except HTTPException:
        # Re-lanzar errores validados (422/400) tal cual, sin convertirlos en 500
        raise
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando checkout: {e}")
    finally:
        db.close()


# -------- Consultar orden por session_id --------
@router.get("/{session_id}")
async def get_order(session_id: str):
    """
    Retorna los detalles de una orden guardada por session_id.
    """
    db = _get_db()
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
