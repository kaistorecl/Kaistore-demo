# routers/admin_products.py

import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from db import get_db, get_draft_products, publish_product

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"]
)

# Sube esto como variable de entorno ADMIN_SECRET en Render
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")


@router.get("/drafts")
def list_drafts(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Devuelve los productos que están en 'draft'.
    Esto es lo que vas a mostrar en /dashboard para decidir qué publicar.
    """
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")

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
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")

    updated = publish_product(db, product_id, price)
    if not updated:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return {
        "status": "ok",
        "message": "Producto publicado",
        "id": updated.id,
        "new_price": updated.price,
    }
