# catalog_public.py
#
# Endpoints públicos de catálogo.
#
# Paso A:
#  - /products/published ahora convierte las columnas reales (title, description,
#    image_url, price...) en el formato que el front espera
#    (title_marketing, short_bullets[], image_urls[]).
#
# Así evitamos los null en la tienda.

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from db import SessionLocal
from models import Product

router = APIRouter(prefix="/api", tags=["products-public"])


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
            out.append(
                {
                    "id": p.id,
                    # lo que el front llama title_marketing = nuestra columna title
                    "title_marketing": p.title,
                    # short_bullets = lista, usando description como 1er bullet
                    "short_bullets": [p.description] if p.description else [],
                    "price": p.price,
                    "currency": p.currency,
                    # image_urls = lista, usando image_url como primera imagen
                    "image_urls": [p.image_url] if p.image_url else [],
                }
            )

        return out


@router.get("/products/{product_id}")
def get_product_detail(product_id: int):
    """
    Devuelve detalle de UN producto publicado.
    (Útil si más adelante quieres página /producto/123)
    """
    with SessionLocal() as db:
        p: Optional[Product] = (
            db.query(Product)
            .filter(Product.id == product_id, Product.status == "published")
            .first()
        )

        if not p:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        return {
            "id": p.id,
            "title_marketing": p.title,
            "short_bullets": [p.description] if p.description else [],
            "price": p.price,
            "currency": p.currency,
            "image_urls": [p.image_url] if p.image_url else [],
        }
