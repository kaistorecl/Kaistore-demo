# routers/admin_products.py

import os
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db import (
    get_db,
    get_draft_products,
    publish_product,
    create_demo_draft,
    get_all_products,
)
from models import Product
from ai_products import pick_idea  # <-- nuevo import para IA simulada

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"],
)

# ================================================================
# Auth simple via ?secret=
# ================================================================
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")

def require_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")

# ================================================================
# 0. DEBUG TOTAL
# ================================================================
@router.get("/debug_all")
def debug_all(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Devuelve TODO lo que hay en la tabla products SIN FILTRO.
    Sirve para diagnosticar por qué /drafts y /published devuelven [].
    """
    require_secret(secret)
    rows = get_all_products(db)
    return [
        {
            "id": p.id,
            "title": p.title,
            "status": p.status,
            "price": p.price,
            "currency": p.currency,
            "score": p.score,
            "source_label": p.source_label,
        }
        for p in rows
    ]

# ================================================================
# 1. Crear draft DEMO manual
# ================================================================
@router.get("/seed_demo")
def seed_demo(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Inserta un producto de prueba en estado 'draft'.
    Simula lo que haría la IA.
    """
    require_secret(secret)
    demo = create_demo_draft(db)
    return {
        "status": "ok",
        "message": "Draft creado",
        "draft_id": demo.id,
    }

# ================================================================
# 2. Ver todos los drafts
# ================================================================
@router.get("/drafts")
def list_drafts(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Devuelve solo los productos con estado 'draft'.
    """
    require_secret(secret)
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

# ================================================================
# 3. Publicar un producto (draft → published)
# ================================================================
@router.patch("/products/{product_id}/publish")
def publish_product_endpoint(
    product_id: int,
    secret: str = Query(..., description="Admin token"),
    price: float = Query(..., description="Nuevo precio público"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cambia un producto a 'published' y actualiza su precio.
    """
    require_secret(secret)
    updated = publish_product(db, product_id, price)
    if not updated:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return {
        "status": "ok",
        "message": "Producto publicado",
        "id": updated.id,
        "new_price": updated.price,
    }

# ================================================================
# 4. Auto-generar productos con IA (nuevo)
# ================================================================
@router.post("/auto_generate", summary="Genera un producto (IA simulada) y lo guarda como draft")
def auto_generate_endpoint(
    secret: str = Query(..., description="Admin token"),
    publish: bool = Query(False, description="Publicar inmediatamente"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Genera un producto usando ideas simuladas de IA y lo guarda en la DB.
    Si publish=True, lo publica automáticamente.
    """
    require_secret(secret)

    idea = pick_idea()

    # Crear objeto
    p = Product(
        title_marketing = idea["title_marketing"],
        short_bullets   = idea["short_bullets"],
        image_urls      = idea["image_urls"],
        price           = idea["price"],
        currency        = idea["currency"],
        status          = "draft",
        source_label    = "ai_seed_v1",
        score           = idea.get("score", 0.85),
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    if publish:
        p.status = "published"
        db.add(p)
        db.commit()
        db.refresh(p)

    return {
        "status": "ok",
        "id": p.id,
        "published": p.status == "published",
        "price": p.price,
        "preview": {
            "title_marketing": p.title_marketing,
            "short_bullets": p.short_bullets,
            "image_urls": p.image_urls,
        }
    }
