from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import random

from db import SessionLocal
from models import Product

from config import settings

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-products"],
)

# ==========================
# Helpers internos
# ==========================

ADMIN_SECRET = settings.ADMIN_SECRET


def check_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")


def fake_ai_product_idea() -> Dict[str, Any]:
    """
    Simula una 'idea de producto' que la IA inventaría.
    OJO: Puede incluir campos que NO existen realmente en la tabla.
    Nosotros después filtramos solo lo que sí existe en Product.
    """

    ideas = [
        {
            "title": "Mini ventilador USB silencioso",
            "description": "Ventilador portátil silencioso para escritorio/home office.",
            "image_url": "https://picsum.photos/seed/fan/800/800",
            "price": 4990,
            "currency": settings.CURRENCY,
            "score": random.randint(70, 90),
            "source_label": "ai_seed_v1",
        },
        {
            "title": "Organizador plegable para clóset",
            "description": "Cajón plegable apilable para ropa interior y accesorios.",
            "image_url": "https://picsum.photos/seed/closet-box/800/800",
            "price": 5990,
            "currency": settings.CURRENCY,
            "score": random.randint(70, 90),
            "source_label": "ai_seed_v1",
        },
        {
            "title": "Lámpara LED portátil recargable",
            "description": "Luz cálida con batería USB-C, ideal camping / escritorio.",
            "image_url": "https://picsum.photos/seed/lamp/800/800",
            "price": 9990,
            "currency": settings.CURRENCY,
            "score": random.randint(70, 90),
            "source_label": "ai_seed_v1",
        },
    ]
    return random.choice(ideas)


def db_insert_draft(db: Session, idea: Dict[str, Any]) -> Product:
    """
    Inserta un nuevo producto en estado 'draft'.

    MUY IMPORTANTE:
    SOLO pasamos a Product() las columnas que EXISTEN de verdad en tu tabla.

    Error que viste:
    TypeError: 'description' is an invalid keyword argument for Product
    => significa que Product NO tiene columna 'description'.

    Así que acá NO mandamos 'description'.
    Tampoco mandamos short_bullets[], image_urls[], etc.
    """

    # Campos que sí sabemos que existen en tu DB por lo que vimos en /published y en los logs:
    # - title
    # - price
    # - currency
    # - image_url
    # - status
    # - score
    # - source_label
    #
    # Lo que NO vamos a pasar:
    # - description  (porque causó el TypeError)
    # - short_bullets
    # - image_urls
    # etc.

    new_product = Product(
        title=idea.get("title", None),
        price=idea.get("price", 0),
        currency=idea.get("currency", settings.CURRENCY),
        image_url=idea.get("image_url", None),
        status="draft",
        score=idea.get("score", 0),
        source_label=idea.get("source_label", "ai_seed_v1"),
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


def publish_product_record(db: Session, p: Product, new_price: Optional[int] = None):
    """
    Marca un Product como 'published' y opcionalmente actualiza price.
    """
    p.status = "published"
    if new_price is not None:
        p.price = new_price
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ==========================
# Rutas Admin
# ==========================


@router.get("/debug_all")
def debug_all(secret: str = Query(..., description="Admin token")):
    """
    Devuelve TODO lo que haya en la tabla products, crudo.
    Para debug en desarrollo.
    """
    check_secret(secret)

    with SessionLocal() as db:
        rows = db.query(Product).order_by(Product.id.asc()).all()

        out = []
        for p in rows:
            out.append(
                {
                    "id": p.id,
                    "title": getattr(p, "title", None),
                    "status": getattr(p, "status", None),
                    "price": getattr(p, "price", None),
                    "currency": getattr(p, "currency", None),
                    "image_url": getattr(p, "image_url", None),
                    "score": getattr(p, "score", None),
                    "source_label": getattr(p, "source_label", None),
                }
            )
        return out


@router.get("/seed_demo")
def seed_demo(secret: str = Query(..., description="Admin token")):
    """
    Inserta un producto de prueba en estado 'draft'.
    Sirve para testear sin IA real.
    """
    check_secret(secret)

    idea = {
        "title": "Menos dolor de cuello en 15 minutos frente al PC",
        # "description": "...",  # <- no la usamos porque tu modelo no la soporta
        "image_url": "https://picsum.photos/seed/demo-neck/800/800",
        "price": 12990,
        "currency": settings.CURRENCY,
        "score": 80,
        "source_label": "manual_seed_v1",
    }

    with SessionLocal() as db:
        p = db_insert_draft(db, idea)

    return {
        "status": "ok",
        "message": "Draft creado",
        "draft_id": p.id,
    }


@router.get("/drafts")
def list_drafts(secret: str = Query(..., description="Admin token")):
    """
    Devuelve solo los productos con estado 'draft'.
    Esto lo va a usar tu dashboard admin.
    """
    check_secret(secret)

    with SessionLocal() as db:
        rows = (
            db.query(Product)
            .filter(Product.status == "draft")
            .order_by(Product.id.asc())
            .all()
        )

        out = []
        for p in rows:
            out.append(
                {
                    "id": p.id,
                    "title_marketing": getattr(p, "title", None),
                    "price": getattr(p, "price", None),
                    "status": getattr(p, "status", None),
                    "score": getattr(p, "score", None),
                    "source_label": getattr(p, "source_label", None),
                }
            )

        return out


@router.patch("/products/{product_id}/publish")
def publish_product_endpoint(
    product_id: int,
    secret: str = Query(..., description="Admin token"),
    price: Optional[int] = Query(None, description="Nuevo precio público"),
):
    """
    Cambia un producto a 'published' y ajusta precio.
    """
    check_secret(secret)

    with SessionLocal() as db:
        p = (
            db.query(Product)
            .filter(Product.id == product_id)
            .first()
        )

        if not p:
            raise HTTPException(status_code=404, detail="Producto no existe")

        publish_product_record(db, p, new_price=price)

        return {
            "status": "ok",
            "message": "Producto publicado",
            "id": p.id,
            "new_price": p.price,
        }


@router.post("/auto_generate")
def auto_generate(
    secret: str = Query(..., description="Admin token"),
    publish: bool = Query(
        False,
        description="Publicar inmediatamente (True salta directo a 'published')",
    ),
):
    """
    Genera un producto usando ideas simuladas de IA y lo guarda en la DB.
    Si publish=True, lo marca como 'published'.

    MUY IMPORTANTE:
    - SOLO usamos columnas que EXISTEN en tu tabla 'products' para no chocar
      con 'description', 'short_bullets', 'image_urls', etc.
    - Rellenamos 'title' (que luego tu front trata como 'title_marketing').
    """
    check_secret(secret)

    idea = fake_ai_product_idea()

    with SessionLocal() as db:
        # 1. Creamos el draft
        p = db_insert_draft(db, idea)

        # 2. ¿Publicarlo al tiro?
        if publish:
            publish_product_record(db, p, new_price=idea.get("price"))

        # Previsualización para la respuesta
        preview = {
            "title_marketing": getattr(p, "title", None),
            "price": getattr(p, "price", None),
            "currency": getattr(p, "currency", settings.CURRENCY),
            "status": getattr(p, "status", None),
        }

        return {
            "status": "ok",
            "id": p.id,
            "published": p.status == "published",
            "price": p.price,
            "preview": preview,
        }
