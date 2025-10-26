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

# intenta importar la idea “IA”; si falla, usa un fallback seguro
try:
    from ai_products import pick_idea
except Exception:
    def pick_idea():
        return {
            "title_marketing": "Producto IA de ejemplo",
            "short_bullets": ["Beneficio 1", "Beneficio 2"],
            "price": 5990,
            "currency": "CLP",
            "image_urls": ["https://via.placeholder.com/800x600?text=ai-main"],
            "score": 0.85,
        }

# Inicializa el router
router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"],
)

# ===============================================================
# Autenticación simple vía ?secret=
# ===============================================================
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")

def require_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")

# ===============================================================
# 0. DEBUG TOTAL
# ===============================================================
@router.get("/debug_all")
def debug_all(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Devuelve todos los productos sin filtro, para diagnóstico."""
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

# ===============================================================
# 1. Crear draft DEMO manual
# ===============================================================
@router.get("/seed_demo")
def seed_demo(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Inserta un producto de prueba en estado 'draft'."""
    require_secret(secret)
    demo = create_demo_draft(db)
    return {"status": "ok", "message": "Draft creado", "draft_id": demo.id}

# ===============================================================
# 2. Ver todos los drafts
# ===============================================================
@router.get("/drafts")
def list_drafts(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Devuelve solo los productos con estado 'draft'."""
    require_secret(secret)
    drafts = get_draft_products(db)
    return [
        {
            "id": p.id,
            "title_marketing": getattr(p, "marketing_title", p.title),
            "price": p.price,
            "status": p.status,
            "score": p.score,
            "source_label": p.source_label,
        }
        for p in drafts
    ]

# ===============================================================
# 3. Publicar un draft (cambiar a published)
# ===============================================================
@router.patch("/products/{product_id}/publish")
def publish_product_endpoint(
    product_id: int,
    secret: str = Query(..., description="Admin token"),
    price: float = Query(..., description="Nuevo precio público"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Cambia un producto a 'published' y actualiza su precio."""
    require_secret(secret)
    updated = publish_product(db, product_id, price)
    if not updated:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"status": "ok", "message": "Producto publicado", "id": updated.id, "new_price": updated.price}

# ===============================================================
# 4. Auto-generar productos con IA simulada
# ===============================================================
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

    idea = pick_idea()  # obtiene una idea simulada

    # Crear producto
    p = Product(
        title_marketing=idea["title_marketing"],
        short_bullets=idea["short_bullets"],
        image_urls=idea["image_urls"],
        price=idea["price"],
        currency=idea["currency"],
        status="draft",
        source_label="ai_seed_v1",
        score=idea.get("score", 0.85),
    )

    db.add(p)
    db.commit()
    db.refresh(p)

    # Si publish=True, cambiar el estado
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
        },
    }
