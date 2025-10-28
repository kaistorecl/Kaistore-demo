# routers/admin_products.py
#
# Endpoints "privados" de administración.
# Acá está:
# - seed_demo           (cargar producto de ejemplo)
# - drafts              (listar productos en estado draft)
# - publish             (pasar draft -> published)
# - auto_generate       (crear producto tipo IA)
#
# IMPORTANTE:
#   - NO metemos columnas que NO existen en tu tabla products.
#   - Rellenamos solo:
#       title
#       marketing_title
#       description_long
#       image_url
#       price
#       currency
#       status
#       score
#       source_label
#
#   - Así evitamos el error "TypeError: 'description' is an invalid keyword argument".

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from db import SessionLocal
from models import Product
from settings import settings

router = APIRouter(prefix="/api/admin", tags=["admin-products"])

ADMIN_SECRET = settings.ADMIN_SECRET


# -------------------------
# utils internos
# -------------------------

def ensure_secret(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")


def db_insert_draft(db: Session, idea: dict) -> Product:
    """
    Inserta un producto nuevo en estado draft usando SOLO columnas válidas.
    """
    new_product = Product(
        title=idea["title"],                     # string NOT NULL
        marketing_title=idea["marketing_title"],# nullable=True en modelo
        description_long=idea["description_long"],
        image_url=idea["image_url"],
        price=idea["price"],
        currency=idea["currency"],
        status="draft",
        score=idea["score"],
        source_label=idea["source_label"],
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


def db_publish_product(db: Session, product_id: int, new_price: float):
    """
    Cambia un producto a 'published' y actualiza precio.
    """
    p: Product | None = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    p.status = "published"
    p.price = new_price
    db.commit()
    db.refresh(p)
    return p


def fake_ai_idea() -> dict:
    """
    Genera una "idea de producto" con texto más vendedor y datos coherentes.
    Esto reemplaza la versión anterior que repetía el título y metía imágenes random.
    """

    # Podríamos tener varias plantillas y elegir una al azar en el futuro.
    # De momento dejamos una sola "línea" estilo organizador de clóset.
    # La idea es que marketing_title sea un título de venta corto,
    # y description_long sea un pitch más humano.

    marketing_title = "Organizador plegable premium para clóset (pack 2)"
    internal_title = "Organizador plegable para clóset"  # este va en title (tu columna NOT NULL)

    long_desc = (
        "Mantén tu ropa y accesorios ordenados sin esfuerzo. "
        "Este organizador plegable cabe en casi cualquier clóset y se arma en segundos. "
        "Ideal para poleras, ropa interior o accesorios pequeños, "
        "sin necesidad de instalación permanente."
    )

    # Imagen que al menos parezca producto hogareño / lifestyle
    # picsum es random igual, pero usamos categorías más cálidas (interiores / hogar).
    # Si quieres más control después podemos pasar a URLs propias subidas a Cloudinary o S3.
    image_url = "https://picsum.photos/seed/closet-organizer/800/800"

    idea = {
        "title": internal_title,
        "marketing_title": marketing_title,
        "description_long": long_desc,
        "image_url": image_url,
        "price": 5990,
        "currency": "CLP",
        "score": 0.90,
        "source_label": "ai_seed_v2",
    }
    return idea


# -------------------------
# Rutas
# -------------------------

@router.get("/debug_all")
def debug_all(secret: str = Query(..., description="Admin token")):
    """
    Devuelve TODOS los productos (cuidado: muestra también draft).
    Sirve solo para debugging.
    """
    ensure_secret(secret)

    with SessionLocal() as db:
        rows = (
            db.query(Product)
            .order_by(desc(Product.id))
            .all()
        )

        out = []
        for p in rows:
            out.append({
                "id": p.id,
                "title": p.title,
                "marketing_title": p.marketing_title,
                "status": p.status,
                "price": p.price,
                "currency": p.currency,
                "image_url": p.image_url,
                "score": p.score,
                "source_label": p.source_label,
            })
        return out


@router.get("/seed_demo")
def seed_demo(secret: str = Query(..., description="Admin token")):
    """
    Inserta un producto DEMO fijo como draft.
    Pensado para probar rápido sin IA.
    """
    ensure_secret(secret)

    demo_idea = {
        "title": "Lámpara LED portátil recargable",
        "marketing_title": "Lámpara LED portátil recargable",
        "description_long": (
            "Iluminación donde quieras. Batería USB recargable, luz cálida "
            "y formato compacto para velador, camping o escritorio."
        ),
        "image_url": "https://picsum.photos/seed/lampara-led/800/800",
        "price": 9990,
        "currency": "CLP",
        "score": 0.8,
        "source_label": "manual_seed_v1",
    }

    with SessionLocal() as db:
        new_p = db_insert_draft(db, demo_idea)

    return {
        "status": "ok",
        "message": "Draft creado",
        "draft_id": new_p.id,
    }


@router.get("/drafts")
def list_drafts(secret: str = Query(..., description="Admin token")):
    """
    Devuelve SOLO productos en estado 'draft'.
    Esto es lo que un futuro dashboard admin va a listar.
    """
    ensure_secret(secret)

    with SessionLocal() as db:
        rows = (
            db.query(Product)
            .filter(Product.status == "draft")
            .order_by(desc(Product.id))
            .all()
        )

        out = []
        for p in rows:
            out.append({
                "id": p.id,
                "title": p.title,
                "marketing_title": p.marketing_title,
                "price": p.price,
                "status": p.status,
                "score": p.score,
                "source_label": p.source_label,
            })
        return out


@router.patch("/products/{product_id}/publish")
def publish_product(
    product_id: int,
    secret: str = Query(..., description="Admin token"),
    price: float = Query(..., description="Nuevo precio público"),
):
    """
    Cambia un producto a 'published' y ajusta el precio.
    """
    ensure_secret(secret)

    with SessionLocal() as db:
        p = db_publish_product(db, product_id, price)

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
    Genera un producto tipo IA y lo guarda en la DB.
    Si publish=True lo deja como 'published'; si no, queda 'draft'.

    MUY IMPORTANTE:
    - SOLO usamos columnas que EXISTEN en tu tabla 'products'; para no chocar con
      columnas inexistentes tipo 'short_bullets[]', 'image_urls', etc.
    - Rellenamos 'title' (que el front luego trata como 'title_marketing'),
      'marketing_title', y 'description_long' con texto más humano.
    """
    ensure_secret(secret)

    idea = fake_ai_idea()

    with SessionLocal() as db:
        new_p = db_insert_draft(db, idea)

        if publish:
            _ = db_publish_product(db, new_p.id, idea["price"])

    # Devolvemos un preview cómodo pa debug
    return {
        "status": "ok",
        "id": new_p.id,
        "published": publish,
        "price": idea["price"],
        "preview": {
            "marketing_title": idea["marketing_title"],
            "price": idea["price"],
            "currency": idea["currency"],
            "status": "published" if publish else "draft",
        },
    }
