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

# Intentamos importar la "idea IA" simulada
# Si falla, usamos un fallback local para no romper.
try:
    from ai_products import pick_idea
except Exception:
    def pick_idea():
        return {
            "title_marketing": "Producto IA de ejemplo",
            "price": 7990,
            "currency": "CLP",
            "image_urls": [
                "https://via.placeholder.com/800x600?text=ai-main",
                "https://via.placeholder.com/800x600?text=ai-side",
            ],
            "score": 87,
        }

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"],
)

# =============================================================================
# Auth simple via ?secret=
# =============================================================================

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")


def require_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")


# =============================================================================
# 0. DEBUG TOTAL
# =============================================================================

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
            "title_marketing": getattr(p, "title_marketing", None),
            "status": getattr(p, "status", None),
            "price": getattr(p, "price", None),
            "currency": getattr(p, "currency", None),
            "score": getattr(p, "score", None),
            "source_label": getattr(p, "source_label", None),
        }
        for p in rows
    ]


# =============================================================================
# 1. Crear draft DEMO manual
# =============================================================================

@router.get("/seed_demo")
def seed_demo(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Inserta un producto de prueba en estado 'draft'.
    Simula lo que haría la IA, pero con datos fijos que sabemos que funcionan.
    """
    require_secret(secret)
    demo = create_demo_draft(db)
    return {
        "status": "ok",
        "message": "Draft creado",
        "draft_id": demo.id,
    }


# =============================================================================
# 2. Ver todos los drafts
# =============================================================================

@router.get("/drafts")
def list_drafts(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Devuelve solo los productos con estado 'draft'.
    Esto es lo que tu dashboard (futuro) debería mostrar.
    """
    require_secret(secret)
    drafts = get_draft_products(db)
    return [
        {
            "id": p.id,
            "title_marketing": getattr(p, "title_marketing", None),
            "price": getattr(p, "price", None),
            "status": getattr(p, "status", None),
            "score": getattr(p, "score", None),
            "source_label": getattr(p, "source_label", None),
        }
        for p in drafts
    ]


# =============================================================================
# 3. Publicar un producto (draft -> published)
# =============================================================================

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


# =============================================================================
# 4. Auto-generar productos con IA simulada (arreglado)
# =============================================================================
@router.post("/auto_generate", summary="Genera un producto (IA simulada) y lo guarda como draft")
def auto_generate_endpoint(
    secret: str = Query(..., description="Admin token"),
    publish: bool = Query(False, description="Publicar inmediatamente"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Genera un producto usando ideas simuladas de IA y lo guarda en la DB.
    Si publish=True, lo publica automáticamente.

    Ajustado para tu modelo real:
    - Usa marketing_title (no title_marketing).
    - No pasa short_bullets porque en tu modelo eso no existe.
    """

    # 1. seguridad
    require_secret(secret)

    # 2. obtener una idea simulada
    idea = pick_idea()

    # 3. crear el draft en la base con SOLO columnas reales del modelo Product
    p = Product(
        marketing_title=idea.get("title_marketing", "Producto IA misterioso"),
        price=idea.get("price", 9990),
        currency=idea.get("currency", "CLP"),
        status="draft",
        source_label="ai_seed_v1",
        score=idea.get("score", 85),
        image_urls=idea.get("image_urls", []),
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    # 4. si publish=True lo marcamos como publicado
    if publish:
        p.status = "published"
        db.add(p)
        db.commit()
        db.refresh(p)

    # 5. responder
    return {
        "status": "ok",
        "id": p.id,
        "published": (p.status == "published"),
        "price": p.price,
        "preview": {
            # OJO: ahora sacamos el título desde marketing_title
            "title_marketing": getattr(p, "marketing_title", None),
            # tu modelo no tenía short_bullets obligatorio, así que no lo devolvemos
            "image_urls": getattr(p, "image_urls", []),
        },
    }
