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

# Intentar importar la IA simulada; si falla, usar fallback seguro.
try:
    from ai_products import pick_idea
except Exception:
    def pick_idea():
        # Fallback simple por si ai_products.py no carga.
        return {
            "title_marketing": "Producto IA de ejemplo",
            "price": 7990,
            "currency": "CLP",
            "score": 85,
        }

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"],
)

# =====================================================================
# Auth simple via ?secret=
# =====================================================================

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")

def require_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")


# =====================================================================
# 0. DEBUG TOTAL
# =====================================================================

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
            "marketing_title": getattr(p, "marketing_title", None),
            "status": p.status,
            "price": p.price,
            "currency": p.currency,
            "score": p.score,
            "source_label": p.source_label,
        }
        for p in rows
    ]


# =====================================================================
# 1. Crear draft DEMO manual (lo que antes hacías como "seed_demo")
# =====================================================================

@router.get("/seed_demo", summary="Seed Demo")
def seed_demo(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Inserta un producto de prueba en estado 'draft'.
    Simula lo que haría la IA, pero con datos hardcodeados.
    """
    require_secret(secret)
    demo = create_demo_draft(db)
    return {
        "status": "ok",
        "message": "Draft creado",
        "draft_id": demo.id,
    }


# =====================================================================
# 2. Ver todos los drafts (estado = 'draft')
# =====================================================================

@router.get("/drafts", summary="List Drafts")
def list_drafts(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Devuelve solo los productos con estado 'draft'.
    Esto es lo que tu dashboard (futuro panel admin) va a mostrar.
    """
    require_secret(secret)
    drafts = get_draft_products(db)
    return [
        {
            "id": p.id,
            # OJO: en la DB la columna podría ser marketing_title,
            # pero en la respuesta pública usamos title_marketing.
            "title_marketing": getattr(p, "marketing_title", p.title),
            "price": p.price,
            "status": p.status,
            "score": p.score,
            "source_label": p.source_label,
        }
        for p in drafts
    ]


# =====================================================================
# 3. Publicar un producto (cambiar draft -> published)
# =====================================================================

@router.patch("/products/{product_id}/publish", summary="Publish Product Endpoint")
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


# =====================================================================
# 4. Auto-generar productos con IA simulada
# =====================================================================

@router.post("/auto_generate", summary="Genera un producto (IA simulada) y lo guarda como draft")
def auto_generate_endpoint(
    secret: str = Query(..., description="Admin token"),
    publish: bool = Query(False, description="Publicar inmediatamente"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Genera un producto usando ideas simuladas de IA y lo guarda en la DB.
    Si publish=True, lo marca como 'published'.

    MUY IMPORTANTE:
    - SOLO usamos columnas que SABEMOS que existen en tu tabla 'products',
      para no crashear con columnas inexistentes como short_bullets o image_urls.
    """

    # 1. Seguridad
    require_secret(secret)

    # 2. Idea simulada de IA
    idea = pick_idea()

    # Sacamos valores seguros de esa idea
    marketing_title_value = idea.get("title_marketing", "Producto IA misterioso")
    price_value = idea.get("price", 9990)
    currency_value = idea.get("currency", "CLP")
    score_value = idea.get("score", 85)

    # 3. Creamos un draft en la DB
    #    NOTA: usamos "marketing_title=" porque en tu DB ya vimos
    #    que luego /drafts responde con "title_marketing".
    #    Eso significa que probablemente la columna real es marketing_title.
    p = Product(
        marketing_title=marketing_title_value,
        price=price_value,
        currency=currency_value,
        status="draft",
        source_label="ai_seed_v1",
        score=score_value,
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    # 4. Si publish=True => pasamos a 'published'
    if publish:
        p.status = "published"
        db.add(p)
        db.commit()
        db.refresh(p)

    # 5. Respondemos algo amigable para que Swagger te muestre
    #    qué se creó
    return {
        "status": "ok",
        "id": p.id,
        "published": (p.status == "published"),
        "price": p.price,
        "preview": {
            "title_marketing": getattr(p, "marketing_title", None),
            "price": p.price,
            "currency": getattr(p, "currency", None),
            "status": p.status,
        },
    }
