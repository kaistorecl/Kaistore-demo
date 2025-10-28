# admin_products.py
#
# Rutas de administración:
# - seed_demo
# - drafts
# - publish
# - auto_generate (IA simulada)
#
# Cambios CLAVE del Paso A:
#  - auto_generate ahora MAPEa la idea linda a las columnas reales de la tabla
#    antes de guardar (title, description, image_url, price...)
#  - Así, cuando luego publiques => el product ya tiene info útil
#    y el catálogo público puede reconstruir title_marketing, etc.

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from db import SessionLocal
from models import Product
from config import settings
from ai_products import generate_fake_product_idea

router = APIRouter(prefix="/api/admin", tags=["admin-products"])

# Leemos tu token admin desde env (Render)
ADMIN_SECRET = settings.ADMIN_SECRET


def require_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")


@router.get("/seed_demo")
def seed_demo(secret: str = Query(..., description="Admin token")):
    """
    Inserta un producto de prueba en estado 'draft'.
    Antes esto tenía valores inventados. Lo dejamos
    como un ejemplo 'manual_seed_v1'.
    """
    require_secret(secret)

    with SessionLocal() as db:
        p = Product(
            title="Mini ventilador USB silencioso",
            description="Enfría sin ruido en videollamadas o mientras duermes",
            image_url="https://via.placeholder.com/800x800?text=ventilador-main",
            price=4990,
            currency=settings.CURRENCY,
            status="draft",
            score=80,
            source_label="manual_seed_v1",
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        return {
            "status": "ok",
            "message": "Draft creado",
            "draft_id": p.id,
        }


@router.get("/drafts")
def list_drafts(secret: str = Query(..., description="Admin token")):
    """
    Devuelve todos LOS DRAFTS (status='draft').
    Esto es lo que tu dashboard admin debería listar.
    """
    require_secret(secret)

    with SessionLocal() as db:
        rows = (
            db.query(Product)
            .filter(Product.status == "draft")
            .order_by(Product.id.desc())
            .all()
        )

        out = []
        for p in rows:
            out.append(
                {
                    "id": p.id,
                    "title_marketing": p.title,
                    "price": p.price,
                    "status": p.status,
                    "score": p.score,
                    "source_label": p.source_label,
                }
            )

        return out


@router.patch("/products/{product_id}/publish")
def publish_product(
    product_id: int,
    secret: str = Query(..., description="Admin token"),
    price: int = Query(..., description="Nuevo precio público"),
):
    """
    Cambia un producto a status='published' y actualiza su price.
    Esto es lo que estás usando para "mandarlo a la tienda".
    """
    require_secret(secret)

    with SessionLocal() as db:
        p: Optional[Product] = db.query(Product).filter(Product.id == product_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Producto no existe")

        p.status = "published"
        p.price = price
        db.commit()
        db.refresh(p)

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
    Genera un producto 'falso IA' y lo guarda.
    Paso A:
    - Tomamos la idea (que tiene title_marketing, short_bullets[], image_urls[])
    - La traducimos a las columnas REALES de Product:
        title        <- idea["title_marketing"]
        description  <- idea["short_bullets"][0] si existe
        image_url    <- idea["image_urls"][0] si existe
        price        <- idea["price"]
        currency     <- idea["currency"]
        status       <- 'draft' o 'published'
    Luego respondemos con un preview.
    """
    require_secret(secret)

    idea = generate_fake_product_idea()

    marketing_title = idea.get("title_marketing", "").strip() or "Producto nuevo"
    bullets = idea.get("short_bullets") or []
    first_bullet = bullets[0] if bullets else ""
    imgs = idea.get("image_urls") or []
    main_img = imgs[0] if imgs else "https://via.placeholder.com/800x800?text=producto"

    status_to_save = "published" if publish else "draft"

    with SessionLocal() as db:
        p = Product(
            title=marketing_title,
            description=first_bullet,
            image_url=main_img,
            price=idea.get("price", 0),
            currency=idea.get("currency", settings.CURRENCY),
            status=status_to_save,
            score=80,
            source_label="ai_seed_v1",
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        return {
            "status": "ok",
            "id": p.id,
            "published": p.status == "published",
            "price": p.price,
            "preview": {
                "title_marketing": p.title,
                "short_bullet": p.description,
                "price": p.price,
                "currency": p.currency,
                "status": p.status,
            },
        }
