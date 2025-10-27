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

# Intentar importar pick_idea desde ai_products.py.
# Si falla por cualquier motivo, usamos un fallback seguro
try:
    from ai_products import pick_idea
except Exception:
    def pick_idea():
        return {
            "title_marketing": "Producto IA de ejemplo",
            "short_bullets": [
                "Beneficio 1",
                "Beneficio 2",
                "Beneficio 3",
            ],
            "price": 5990,
            "currency": "CLP",
            "image_urls": [
                "https://via.placeholder.com/800x600?text=ai-main",
                "https://via.placeholder.com/800x600?text=ai-side",
            ],
            "score": 0.85,
        }

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"],
)

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
    """
    DEVUELVE TODO lo que hay en la tabla products SIN FILTRO.
    Sirve para diagnosticar por qué /drafts y /published devuelven [].
    """
    require_secret(secret)

    rows = get_all_products(db)
    return [
        {
            "id": p.id,
            "title": getattr(p, "title", None),
            "marketing_title": getattr(p, "marketing_title", None),
            "status": p.status,
            "price": p.price,
            "currency": p.currency,
            "score": getattr(p, "score", None),
            "source_label": getattr(p, "source_label", None),
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


# =========================================================
# 2. Ver todos los drafts
# =========================================================
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
            "title_marketing": getattr(p, "marketing_title", None) or getattr(p, "title", None),
            "price": p.price,
            "status": p.status,
            "score": getattr(p, "score", None),
            "source_label": getattr(p, "source_label", None),
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


# =========================================================
# 4. Auto-generar productos con IA simulada
# =========================================================
@router.post(
    "/auto_generate",
    summary="Genera un producto (IA simulada) y lo guarda como draft",
)
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

    # Paso 1: intentar sacar una idea de ai_products
    try:
        idea = pick_idea()
    except Exception as e:
        # Si por alguna razón pick_idea rompe, devolvemos fallback
        idea = {
            "title_marketing": "Producto IA fallback",
            "short_bullets": [
                "Alivia dolores al instante",
                "Diseño ergonómico",
                "Ideal para home office",
            ],
            "price": 9990,
            "currency": "CLP",
            "image_urls": [
                "https://via.placeholder.com/800x600?text=fallback-main",
            ],
            "score": 0.9,
        }

    # Aseguramos que no reviente si falta alguna key
    title_marketing = idea.get("title_marketing", "Producto sin título")
    short_bullets = idea.get("short_bullets", [])
    image_urls = idea.get("image_urls", [])
    price = idea.get("price", 9990)
    currency = idea.get("currency", "CLP")
    score_val = idea.get("score", 0.85)

    try:
        # Paso 2: crear el objeto Product
        # IMPORTANTE:
        # - ponemos BOTH title y marketing_title por si el modelo usa uno u otro
        p = Product(
            marketing_title=title_marketing,
            title=title_marketing,
            short_bullets=short_bullets,
            image_urls=image_urls,
            price=price,
            currency=currency,
            status="draft",
            source_label="ai_seed_v1",
            score=score_val,
        )

        # guardamos draft
        db.add(p)
        db.commit()
        db.refresh(p)

        # Paso 3: si publish=True -> marcar como published
        if publish:
            p.status = "published"
            db.add(p)
            db.commit()
            db.refresh(p)

        # Paso 4: responder bonito
        return {
            "status": "ok",
            "id": p.id,
            "published": (p.status == "published"),
            "price": p.price,
            "preview": {
                "title_marketing": getattr(p, "marketing_title", None),
                "short_bullets": getattr(p, "short_bullets", []),
                "image_urls": getattr(p, "image_urls", []),
            },
        }

    except Exception as e:
        # Si algo falla al crear/guardar el Product, NO tiramos 500.
        # Devolvemos info para debug sin botar el server.
        return {
            "status": "error",
            "message": str(e),
            "idea_used": idea,
            }
