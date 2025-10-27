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

# Intentar importar la idea IA simulada
try:
    from ai_products import pick_idea
except Exception:
    # Fallback por si ai_products falla por cualquier motivo
    def pick_idea():
        return {
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


router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"],
)

# ============================================================
# Auth simple vía ?secret=
# ============================================================

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "CAMBIA_ESTO_POR_UN_TOKEN_LARGO")


def require_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")


# ============================================================
# 0. DEBUG TOTAL
# ============================================================
@router.get("/debug_all", summary="Debug All")
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

    # devolvemos todos los campos importantes crudos
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


# ============================================================
# 1. Crear draft DEMO manual (lo que hacía seed_demo antes)
# ============================================================
@router.get("/seed_demo", summary="Seed Demo")
def seed_demo(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Inserta un producto de prueba en estado 'draft'.
    Simula lo que haría la IA, pero con datos fijos.
    """
    require_secret(secret)

    demo = create_demo_draft(db)

    return {
        "status": "ok",
        "message": "Draft creado",
        "draft_id": demo.id,
    }


# ============================================================
# 2. Ver todos los drafts
# ============================================================
@router.get("/drafts", summary="List Drafts")
def list_drafts(
    secret: str = Query(..., description="Admin token"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Devuelve solo los productos con estado 'draft'.
    Esto es lo que tu dashboard (futuro panel admin) debería mostrar.
    """
    require_secret(secret)

    drafts = get_draft_products(db)

    return [
        {
            "id": p.id,
            # usamos marketing_title si existe, si no fallback a title
            "title_marketing": getattr(p, "marketing_title", None) or getattr(p, "title", None),
            "price": p.price,
            "status": p.status,
            "score": getattr(p, "score", None),
            "source_label": getattr(p, "source_label", None),
        }
        for p in drafts
    ]


# ============================================================
# 3. Publicar un producto (draft -> published)
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
# 4. Auto-generar productos con IA simulada
# ============================================================
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

    # Paso 1: obtener idea de IA (pick_idea o fallback)
    try:
        idea = pick_idea()
    except Exception:
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

    # Sacamos los datos relevantes de la idea
    title_marketing = idea.get("title_marketing", "Producto sin título")
    short_bullets = idea.get("short_bullets", [])
    image_urls = idea.get("image_urls", [])
    price_val = idea.get("price", 9990)
    currency_val = idea.get("currency", "CLP")
    score_val = idea.get("score", 0.85)

    try:
        # Paso 2: crear el Product en la BD
        # IMPORTANTE:
        #   NO ponemos short_bullets ni image_urls aquí porque
        #   tu modelo Product NO tiene esas columnas.
        #
        # Usamos únicamente columnas que sí existen en la tabla.
        p = Product(
            # muchos modelos tienen ambos: title y/o marketing_title, así que seteamos ambos igual
            marketing_title=title_marketing,
            title=title_marketing,
            price=price_val,
            currency=currency_val,
            status="draft",
            source_label="ai_seed_v1",
            score=score_val,
        )

        db.add(p)
        db.commit()
        db.refresh(p)

        # Paso 3: si publish=True, cambiar estado a "published"
        if publish:
            p.status = "published"
            db.add(p)
            db.commit()
            db.refresh(p)

        # Paso 4: devolver respuesta bonita
        return {
            "status": "ok",
            "id": p.id,
            "published": (p.status == "published"),
            "price": p.price,
            "preview": {
                "title_marketing": title_marketing,
                "short_bullets": short_bullets,
                "image_urls": image_urls,
            },
        }

    except Exception as e:
        # Si algo revienta (por ejemplo, constraint en BD),
        # devolvemos info de depuración
        return {
            "status": "error",
            "message": str(e),
            "idea_used": idea,
    }
