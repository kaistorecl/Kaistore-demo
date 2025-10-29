# routers/orders.py
from fastapi import APIRouter, Request, HTTPException
from db import SessionLocal
from models import Product
from config import settings   # <- en tu repo es config.py, por eso importamos así
import stripe

router = APIRouter(prefix="/api/orders", tags=["orders"])

@router.post("/checkout", summary="Create Checkout Session")
async def create_checkout(request: Request):
    """
    Acepta:
      - {"items":[{"product_id": 1, "qty": 1}]}
      - {"items":[{"title":"...", "price":4990, "quantity":1, "currency":"CLP"}]}

    Fallback (para Swagger cuando no deja editar body):
      /api/orders/checkout?product_id=1&qty=1
    """
    # 1) Intentar leer JSON
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = None
    except Exception:
        payload = None

    # 2) Fallback desde query params si no vino JSON
    if not payload or "items" not in payload:
        qp = request.query_params
        if "product_id" in qp:
            try:
                pid = int(qp["product_id"])
                qty = int(qp.get("qty", "1"))
                payload = {"items": [{"product_id": pid, "qty": qty}]}
            except Exception:
                raise HTTPException(status_code=400, detail="JSON inválido")
        else:
            raise HTTPException(status_code=400, detail="JSON inválido")

    items = payload.get("items", [])
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="JSON inválido: 'items' vacío")

    # 3) Preparar line_items para Stripe
    line_items = []
    with SessionLocal() as db:
        for it in items:
            # Caso A: por product_id
            if isinstance(it, dict) and "product_id" in it:
                pid = int(it["product_id"])
                qty = int(it.get("qty") or it.get("quantity") or 1)

                p = (
                    db.query(Product)
                    .filter(Product.id == pid, Product.status == "published")
                    .first()
                )
                if not p:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Producto {pid} no encontrado/publicado",
                    )

                line_items.append(
                    {
                        "price_data": {
                            "currency": (p.currency or settings.CURRENCY).lower(),
                            "product_data": {"name": p.title},
                            "unit_amount": int(float(p.price)) * 100,
                        },
                        "quantity": qty,
                    }
                )
            # Caso B: datos sueltos
            elif isinstance(it, dict) and "title" in it and "price" in it:
                qty = int(it.get("quantity") or it.get("qty") or 1)
                currency = (it.get("currency") or settings.CURRENCY).lower()
                line_items.append(
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {"name": it["title"]},
                            "unit_amount": int(float(it["price"])) * 100,
                        },
                        "quantity": qty,
                    }
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "JSON inválido: cada item debe tener "
                        "product_id/qty o title/price/quantity/currency"
                    ),
                )

    if not line_items:
        raise HTTPException(status_code=400, detail="No hay items válidos")

    # 4) Crear sesión de pago en Stripe
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        success_url = f"{settings.WEB_URL}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.WEB_URL}/cancel"

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {"url": session.url}
    except Exception as e:
        print("Stripe error:", repr(e))
        raise HTTPException(status_code=500, detail="Error al crear sesión de pago")


@router.get("/{session_id}", summary="Get Order (Stripe session)")
def get_order(session_id: str):
    """Devuelve info básica de la sesión (útil para depurar)."""
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        s = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": s.id,
            "status": s.status,
            "amount_total": s.amount_total,
            "currency": s.currency,
            "payment_status": s.payment_status,
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
