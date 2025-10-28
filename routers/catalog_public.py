# routers/catalog_public.py
#
# Endpoints públicos de catálogo (lo que usa la tienda para renderizar).
#
# Importante:
# - No exponemos info interna rara, solo lo que el front necesita.
# - Formateamos los datos de la BD (products) al formato esperado por el front:
#   {
#       "id": 1,
#       "title_marketing": "...",
#       "short_bullets": ["...", "..."],
#       "price": 5990,
#       "currency": "CLP",
#       "image_urls": ["https://..."]
#   }

from fastapi import APIRouter, HTTPException
from typing import List

from db import SessionLocal
from models import Product

router = APIRouter(
    prefix="/api",
    tags=["products-public"],
)

@router.get("/products/published")
def list_published_products():
    """
    Devuelve TODOS los productos con status='published'
    en un formato seguro para mostrarlos en la tienda pública.
    """

    with SessionLocal() as db:
        rows: List[Product] = (
            db.query(Product)
            .filter(Product.status == "published")
            .order_by(Product.id.desc())
            .all()
        )

    out = []
    for p in rows:
        out.append({
            "id": p.id,
            # título "de vitrina": marketing_title si existe, si no title
            "title_marketing": p.marketing_title or p.title or "",
            # short_bullets es una lista. Si no tenemos bullets reales aún,
            # metemos al menos 1 bullet con el título para que el front no quede vacío.
            "short_bullets": [p.marketing_title or p.title] if (p.marketing_title or p.title) else [],
            "price": p.price,
            "currency": p.currency,
            # image_urls debe ser una lista. Usamos image_url como primera foto.
            "image_urls": [p.image_url] if p.image_url else [],
        })

    return out


@router.get("/products/{product_id}")
def get_product_detail(product_id: int):
    """
    Devuelve detalle de UN producto publicado.
    Útil más adelante si quieres /producto/123 en el front.
    """
    with SessionLocal() as db:
        p: Product = (
            db.query(Product)
            .filter(Product.id == product_id, Product.status == "published")
            .first()
        )

    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return {
        "id": p.id,
        "title_marketing": p.marketing_title or p.title or "",
        "short_bullets": [p.marketing_title or p.title] if (p.marketing_title or p.title) else [],
        "price": p.price,
        "currency": p.currency,
        "image_urls": [p.image_url] if p.image_url else [],
    }
