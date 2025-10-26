# routers/admin_products.py

import os
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from db import get_db, get_draft_products, publish_product
from models import Product

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"]
)

# =========================================
# Auth simple con token secreto
# =========================================
# Puedes setear ADMIN_SECRET como variable de entorno en Render.
# Si no está seteado, usa el fallback "CAMBIA_ESTO_POR_UN_TOKEN_LARGO".
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")


def _check_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")


# =========================================
# 1) Lista los productos en estado draft
# =========================================
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


# =========================================
# 2) Publicar un draft -> published
# =========================================
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


# =========================================
# 3) NUEVO: seed_demo
#    Crea 1 producto en estado "draft" en la BD,
#    para que luego puedas aprobarlo/publicarlo.
# =========================================
@router.post("/seed_demo")
def seed_demo(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
):
    """
    Inserta un producto DEMO en estado 'draft' directamente en la base.
    Úsalo solo una vez para poblar tu tienda la primera vez.
    Luego podrás verlo en /api/admin/drafts y publicarlo.
    """
    _check_secret(secret)

    demo = Product(
        # estado inicial
        status="draft",

        # texto de marketing
        title="Corrector cervical portátil",
        slug="corrector-cervical-portatil",
        marketing_title="Menos dolor de cuello en 15 minutos frente al PC",
        description_long=(
            "¿Terminas el día con el cuello duro y tensión en la zona cervical? "
            "Este soporte ajustable te ayuda a mantener una postura más cómoda "
            "mientras trabajas o descansas, sin pastillas ni cremas."
        ),

        # bullets de venta (guardados como string JSON)
        bullets_json=json.dumps([
            "Reduce tensión cervical después de horas frente al PC",
            "Úsalo sentado mientras trabajas",
            "Sin pastillas ni cremas",
            "Ajustable y cómodo"
        ]),

        # FAQ (también string JSON)
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

        # nota de advertencia
        risk_note="No apretar demasiado. No usar mientras duermes.",

        # imágenes
        image_url="https://via.placeholder.com/400x400?text=Corrector+Cervical",
        image_urls_json=json.dumps([
            "https://via.placeholder.com/400x400?text=Corrector+Cervical",
            "https://via.placeholder.com/400x400?text=Vista+Lateral"
        ]),

        # precios base inicial (lo podemos ajustar al publicar)
        price=12990,
        currency="CLP",

        # meta interna
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
        "message": "Producto demo creado en draft",
        "draft_id": demo.id,
    }
