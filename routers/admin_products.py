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

# ============================================================
# IA simulada / fallback
# ============================================================

try:
    from ai_products import pick_idea
except Exception:
    def pick_idea():
        # fallback seguro si ai_products.py no está o falla
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

# ============================================================
# auth simple con ?secret=
# ============================================================

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")

def require_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")


# ============================================================
# DEBUG TOTAL
# ============================================================

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
            "title": getattr(p, "title", None),
            "marketing_title": getattr(p, "marketing_title", None),
            "status": getattr(p, "status", None),
            "price": getattr(p, "price", None),
            "currency": getattr(p, "currency", None),
            "score": getattr(p, "score", None),
            "source_label": getattr(p, "source_label", None),
        }
        for p in rows
    ]


# ============================================================
# SEED DEMO (insertar un draft de prueba)
# ============================================================

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


# ============================================================
# LISTAR DRAFTS
# ============================================================

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

    out: List[Dict[str, Any]] = []
    for p in drafts:
        out.append(
            {
                "id": p.id,
                # Lo que mostramos al admin:
                "title_marketing": getattr(p, "marketing_title", getattr(p, "title", "")),
                "price": getattr(p, "price", None),
                "status": getattr(p, "status", None),
                "score": getattr(p, "score", None),
                "source_label": getattr(p, "source_label", None),
            }
        )
    return out


# ============================================================
# PUBLICAR DRAFT (cambiar a published + actualizar precio)
# ============================================================

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


# ============================================================
# AUTO-GENERATE (IA simulada)
# ============================================================

@router.post(
    "/auto_generate",
    summary="Genera un producto (IA simulada) y lo guarda como draft",
)
def auto_generate_endpoint(
    secret: str = Query(..., description="Admin token"),
    publish: bool = Query(
        False,
        description="Publicar inmediatamente (True salta directo a 'published')",
    ),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Genera un producto usando ideas simuladas de IA y lo guarda en la DB.
    Si publish=True, lo marca como 'published'.

    MUY IMPORTANTE:
    - SOLO usamos columnas que SABEMOS que existen en tu tabla 'products',
      para no crashear con columnas inexistentes como short_bullets o image_urls.
    - Además rellenamos tanto `title` como `marketing_title`, porque
      muchos modelos de Producto requieren `title` NOT NULL.
    """

    # 1. Seguridad
    require_secret(secret)

    # 2. Obtener idea IA simulada (o fallback)
    idea = pick_idea()

    marketing_title_value = idea.get("title_marketing", "Producto IA misterioso")
    price_value = idea.get("price", 9990)
    currency_value = idea.get("currency", "CLP")
    score_value = idea.get("score", 85)

    # 3. Crear fila en la DB como draft
    #    IMPORTANTE: seteamos title Y marketing_title,
    #    porque la columna title suele ser obligatoria (NOT NULL).
    p = Product(
        title=marketing_title_value,
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

    # 4. Si publish=True, pasamos a published de inmediato
    if publish:
        p.status = "published"
        db.add(p)
        db.commit()
        db.refresh(p)

    # 5. Devolver preview amigable
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
