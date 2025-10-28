# routers/admin_products.py
#
# Endpoints "admin". Todos protegidos con ?secret=...
# Acá se crean borradores, se listan drafts, se publican, etc.

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import random

from db import SessionLocal
from models import Product
from config import settings  # <- usamos settings.ADMIN_SECRET

router = APIRouter(prefix="/api/admin", tags=["admin-products"])


# -------------------------------------------------
# Helpers internos
# -------------------------------------------------

def check_secret(secret: str):
    if secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")


def fake_ai_idea() -> dict:
    """
    Simula 'la IA inventó un producto'.
    IMPORTANTE: SOLO devolvemos campos que sabemos mapear a columnas reales.
    NADA de short_bullets[], image_urls[], etc. directamente en DB.
    """
    ideas = [
        {
            "title_marketing": "Mini ventilador USB silencioso",
            "description": "Ventilador portátil recargable ideal para escritorio o velador.",
            "image_url": "https://via.placeholder.com/800x800?text=fan",
            "price": 4990,
            "currency": "CLP",
            "score": 82,
        },
        {
            "title_marketing": "Organizador plegable para closet",
            "description": "Mantén tu ropa ordenada y visible. Se pliega para guardar.",
            "image_url": "https://via.placeholder.com/800x800?text=closet",
            "price": 5990,
            "currency": "CLP",
            "score": 78,
        },
        {
            "title_marketing": "Lámpara LED portátil recargable",
            "description": "Luz cálida regulable, ideal para noche o camping.",
            "image_url": "https://via.placeholder.com/800x800?text=lamp",
            "price": 9990,
            "currency": "CLP",
            "score": 88,
        },
    ]
    return random.choice(ideas)


def db_insert_draft(db: Session, idea: dict) -> Product:
    """
    Crea un Product en estado 'draft' usando SOLO columnas reales.
    Hace el mapeo correcto de nombres.
    """

    # columnas que esperamos que EXISTAN realmente en tu tabla Product:
    # - id (autoincrement, lo pone la DB)
    # - title (string, NOT NULL idealmente)
    # - description (string / text, puede ser NULL o no, depende de tu modelo)
    # - image_url (string, puede ser NULL)
    # - price (numérico/float/int)
    # - currency (string, ej "CLP")
    # - status (string: "draft" | "published")
    # - score (int o float)           <-- si no existe en tu modelo, quítalo
    # - source_label (string)         <-- si no existe en tu modelo, quítalo

    marketing_title = idea.get("title_marketing") or "Producto sin nombre"
    description = idea.get("description") or ""
    image_url = idea.get("image_url") or "https://via.placeholder.com/800x800?text=producto"
    price = idea.get("price", 0)
    currency = idea.get("currency", "CLP")
    score = idea.get("score", 0)

    new_product = Product(
        title=marketing_title,         # <- MUY IMPORTANTE: title nunca va NULL
        description=description,
        image_url=image_url,
        price=price,
        currency=currency,
        status="draft",
        score=score,
        source_label="ai_seed_v1",
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


def publish_product_now(db: Session, product: Product, new_price: Optional[float] = None):
    """
    Marca un borrador como 'published' y opcionalmente ajusta precio.
    """
    if new_price is not None:
        product.price = new_price
    product.status = "published"
    db.add(product)
    db.commit()
    db.refresh(product)


# -------------------------------------------------
# ENDPOINTS
# -------------------------------------------------


@router.get("/debug_all")
def debug_all(secret: str = Query(..., description="Admin token")):
    """
    Devuelve TODO lo que haya en la tabla products (cuidado, esto es full debug).
    """
    check_secret(secret)

    with SessionLocal() as db:
        rows = db.query(Product).order_by(Product.id.desc()).all()
        out = []
        for p in rows:
            out.append(
                {
                    "id": p.id,
                    "title": p.title,
                    "description": p.description,
                    "price": p.price,
                    "currency": p.currency,
                    "status": p.status,
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
    Esto es como un mini auto_generate fijo.
    """
    check_secret(secret)

    demo_idea = {
        "title_marketing": "Soporte lumbar para silla",
        "description": "Mejora postura en teletrabajo. Correas universales.",
        "image_url": "https://via.placeholder.com/800x800?text=lumbar",
        "price": 7990,
        "currency": "CLP",
        "score": 90,
    }

    with SessionLocal() as db:
        p = db_insert_draft(db, demo_idea)
        return {
            "status": "ok",
            "message": "Draft creado",
            "draft_id": p.id,
        }


@router.get("/drafts")
def list_drafts(secret: str = Query(..., description="Admin token")):
    """
    Devuelve SOLO los productos con estado 'draft'.
    Esto es lo que tu dashboard (futuro panel admin) va a mostrar.
    """
    check_secret(secret)

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
                    "score": getattr(p, "score", None),
                    "source_label": getattr(p, "source_label", None),
                }
            )
        return out


@router.patch("/products/{product_id}/publish")
def publish_product_endpoint(
    product_id: int,
    secret: str = Query(..., description="Admin token"),
    price: Optional[float] = Query(None, description="Nuevo precio público"),
):
    """
    Cambia un producto a 'published' y actualiza su precio si viene.
    """
    check_secret(secret)

    with SessionLocal() as db:
        p: Optional[Product] = (
            db.query(Product)
            .filter(Product.id == product_id)
            .first()
        )

        if not p:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        publish_product_now(db, p, new_price=price)

        return {
            "status": "ok",
            "message": "Producto publicado",
            "id": p.id,
            "new_price": p.price,
        }


@router.post("/auto_generate")
def auto_generate(
    secret: str = Query(..., description="Admin token"),
    publish: bool = Query(False, description="Publicar inmediatamente (True salta directo a 'published')"),
):
    """
    Genera un producto usando ideas simuladas de IA y lo guarda en la DB.
    Si publish=True, lo marca como 'published' inmediatamente.

    MUY IMPORTANTE:
    - SOLO usamos columnas que SABEMOS que existen en tu tabla 'products',
      para no crashear con columnas inexistentes como short_bullets[] o image_urls[].
    - Además rellenamos tanto 'title' como 'title_marketing' (en nuestra lógica interna),
      porque muchos modelos de Producto requieren que 'title' NOT NULL.
    """
    check_secret(secret)

    idea = fake_ai_idea()

    with SessionLocal() as db:
        # 1. Creamos draft
        p = db_insert_draft(db, idea)

        # 2. ¿publicar altiro?
        if publish:
            publish_product_now(db, p)

        # 3. Respuesta resumida (preview)
        preview = {
            "title_marketing": p.title,
            "price": p.price,
            "currency": p.currency,
            "status": p.status,
        }

        return {
            "status": "ok",
            "id": p.id,
            "published": (p.status == "published"),
            "price": p.price,
            "preview": preview,
        }
