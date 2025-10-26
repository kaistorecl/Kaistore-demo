@router.post("/checkout")
def checkout(payload: CheckoutIn, request: Request):
    """
    Acepta:
      { "items": [ { "product_id": 3, "qty": 1 } ] }
      o bien
      { "items": [ { "title": "...", "price": 4990, "quantity": 1, "currency": "CLP" } ] }
    """
    db = _get_db()
    try:
        line_items = []

        for i, it in enumerate(payload.items):
            # Normalizamos campos
            if it.product_id is not None:
                # Buscar en DB
                prod = db.query(Product).filter(Product.id == it.product_id).first()
                if not prod:
                    raise HTTPException(status_code=400, detail=f"Producto {it.product_id} no existe")
                title = prod.title
                price = float(prod.price)
                quantity = it.qty or 1
                currency = settings.CURRENCY       # p.ej. "CLP"
            else:
                # Validar formato alternativo
                if not (it.title and it.price and it.quantity):
                    raise HTTPException(
                        status_code=422,
                        detail=f"Faltan campos en items[{i}]. Usa product_id/qty o title/price/quantity/currency",
                    )
                title = it.title
                price = float(it.price)
                quantity = int(it.quantity)
                currency = (it.currency or settings.CURRENCY).lower()

            # Stripe usa montos enteros en la moneda menor (centavos)
            unit_amount = int(round(price))

            line_items.append({
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {"name": title},
                    "unit_amount": unit_amount,
                },
                "quantity": quantity,
            })

        # URLs de éxito/cancel
        origin = request.headers.get("origin") or f"https://{request.url.hostname}"
        success_url = f"{origin}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{origin}/cancel"

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        # 👇 clave que espera el front
        return {
            "checkout_url": session.url,
            "id": session.id,
            "url": session.url,
        }
    finally:
        db.close()
