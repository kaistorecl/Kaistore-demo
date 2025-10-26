# routers/admin_products.py

import os
import json
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db import get_db, get_draft_products, publish_product
from models import Product  # <-- importante: necesitamos crear drafts

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"]
)

# Leemos el secreto desde variable de entorno si existe (Render),
# y si no, usamos un fallback por defecto.
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")


def _check_secret(secret: str):
    if secret != ADMIN_SECRET:
        # mismo comportamiento en todos los endpoints admin
        raise HTTPException(status_code=403, detail="No autorizado")


@router.get("/drafts")
def list_drafts(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Devuelve los productos que están en 'draft'.
    Esto es lo que vas a mostrar en /dashboard para decidir qué publicar.
    """
    _check_secret(secret)

    drafts = get_draft_products(db)

    return [
        {
            "id": p.id,
            "title_marketing": p.marketing_title or p.title,
            "price": p.price,
            "status": p.status,
            "score": p.score,
            "source_label": p.source_label,
        }
        for p in drafts
    ]


@router.patch("/products/{product_id}/publish")
def publish_product_endpoint(
    product_id: int,
    secret: str = Query(..., description="Admin token"),
    price: float = Query(..., description="Nuevo precio público"),
    db: Session = Depends(get_db),
):
    """
    Cambia un producto a 'published' y actualiza su precio.
    Esto es lo que hará el botón 'Publicar' en tu panel.
    """
    _check_secret(secret)

    updated = publish_product(db, product_id, price)
    if not updated:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return {
        "status": "ok",
        "message": "Producto publicado",
        "id": updated.id,
        "new_price": updated.price,
    }


@router.get("/seed_demo")
def seed_demo(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
):
    """
    Crea 1 producto demo en estado 'draft'.
    Sirve para probar el flujo completo:
      draft -> /drafts -> /publish -> aparece en vitrina pública.
    """

    _check_secret(secret)

    demo = Product(
        title="Corrector cervical portátil",
        slug="corrector-cervical-portatil",  # tiene unique=True, así que no repitas 1.000 veces
        status="draft",
        marketing_title="Menos dolor de cuello en 15 minutos frente al PC",
        description_long=(
            "¿Terminas el día con el cuello duro y tensión en la zona cervical? "
            "Este soporte ajustable te ayuda a mantener una postura más cómoda "
            "mientras trabajas o descansas, sin pastillas ni cremas."
        ),
        bullets_json=json.dumps([
            "Reduce tensión cervical después de horas frente al PC",
            "Úsalo sentado mientras trabajas",
            "Sin pastillas ni cremas",
            "Ajustable y cómodo"
        ]),
        faq_json=json.dumps([
            {
                "q": "¿Duele usarlo?",
                "a": "No debería doler. Debe sentirse firme pero cómodo."
            },
            {
                "q": "¿Sirve si trabajo 8 horas sentado?",
                "a": "Sí, está pensado para personas que pasan mucho rato frente a pantalla."
            },
            {
                "q": "¿Cuánto demora el envío?",
                "a": "Promedio 2-4 días hábiles según tu zona."
            }
        ]),
        risk_note="No apretar demasiado. No usar mientras duermes.",
        image_url="https://via.placeholder.com/400x400?text=Producto",
        image_urls_json=json.dumps([
            "https://via.placeholder.com/400x400?text=Producto",
            "https://via.placeholder.com/400x400?text=Vista+lateral"
        ]),
        price=12990,
        currency="CLP",
        score=90,
        active=True,
        supplier_sku="cx-neck-relief-v1",
        source_label="manual_seed_v1",
    )

    db.add(demo)
    db.commit()
    db.refresh(demo)

    return {
        "status": "ok",
        "message": "Draft creado",
        "draft_id": demo.id,
    }
