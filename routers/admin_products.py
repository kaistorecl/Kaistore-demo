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

# intentar importar IA; si falla, usar fallback
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

router = APIRouter(prefix="/api/admin", tags=["admin-products"])

# =========================================================
# Auth simple via ?secret=
# =========================================================
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")

def require_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")

# =========================================================
# 0. DEBUG TOTAL
# =========================================================
@router.get("/debug_all")
def debug_all(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Devuelve TODO lo que hay en products SIN FILTRO."""
    require_secret(secret)
    rows = get_all_products(db)
    return [
        {
            "id": p.id,
            "title": getattr(p, "title", None) or getattr(p, "marketing_title", None),
            "status": p.status,
            "price": p.price,
            "currency": p.currency,
            "score": p.score,
            "source_label": p.source_label,
        }
        for p in rows
    ]

# =========================================================
# 1. Crear draft DEMO manual
# =========================================================
@router.get("/seed_demo")
def seed_demo(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Inserta un producto demo en estado 'draft'."""
    require_secret(secret)
    demo = create_demo_draft(db)
    return {"status": "ok", "message": "Draft creado", "draft_id": demo.id}

# =========================================================
# 2. Ver todos los drafts
# =========================================================
@router.get("/drafts")
def list_drafts(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Devuelve solo los productos 'draft'."""
    require_secret(secret)
    drafts = get_draft_products(db)
    return [
        {
            "id": p.id,
            "title_marketing": getattr(p, "marketing_title", None) or getattr(p, "title", None),
            "price": p.price,
            "status": p.status,
            "score": p.score,
            "source_label": p.source_label,
        }
        for p in drafts
    ]

# =========================================================
# 3. Publicar un producto (draft -> published)
# =========================================================
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

# =========================================================
# 4. Auto-generar productos con IA (simulada)
# =========================================================
@router.post("/auto_generate", summary="Genera un producto (IA simulada) y lo guarda como draft")
def auto_generate_endpoint(
    secret: str = Query(..., description="Admin token"),
    publish: bool = Query(False, description="Publicar inmediatamente"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Genera un producto usando una idea simulada de IA:
    - Crea un row en DB con status 'draft'
    - Si publish=True, lo pasa a 'published'
    """
    require_secret(secret)

    idea = pick_idea()  # nunca debiera tirar 500 por el try/except de arriba

    # Compatibilidad: tu modelo puede usar `marketing_title` o `title`
    title_value = idea.get("title_marketing") or idea.get("title")

    p = Product(
        marketing_title=title_value,
        short_bullets=idea.get("short_bullets", []),
        image_urls=idea.get("image_urls", []),
        price=idea.get("price", 5990),
        currency=idea.get("currency", "CLP"),
        status="draft",
        source_label="ai_seed_v1",
        score=idea.get("score", 0.85),
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
            "title_marketing": getattr(p, "marketing_title", None) or getattr(p, "title", None),
            "short_bullets": p.short_bullets,
            "image_urls": p.image_urls,
        },
        }
