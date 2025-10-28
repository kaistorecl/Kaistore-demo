# routers/catalog_public.py
#
# Endpoints públicos del catálogo (lo que consume la tienda / frontend).

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import json

from db import SessionLocal
from models import Product

router = APIRouter(prefix="/api", tags=["products-public"])


def _build_public_record(p: Product) -> dict:
    """
    Convierte una fila Product (ORM) al formato "seguro" que ve el cliente.
    Acá normalizamos nombres y llenamos campos que el front espera.
    """

    # title_marketing:
    # usamos marketing_title si viene, si no caemos a title normal
    marketing = p.marketing_title or p.title or "Producto"

    # short_bullets:
    # en DB tienes bullets_json = Text (string con JSON tipo ["bullet1","bullet2",...])
    bullets_list: List[str] = []
    if p.bullets_json:
        try:
            parsed = json.loads(p.bullets_json)
            if isinstance(parsed, list):
                # nos quedamos con strings no vacíos
                bullets_list = [b for b in parsed if isinstance(b, str) and b.strip()]
        except Exception:
            bullets_list = []

    # si no había bullets_json decente, inventamos 1 bullet desde description_long
    if not bullets_list:
        if p.description_long:
            bullets_list = [p.description_long.strip()[:140]]
        else:
            bullets_list = []

    # image_urls:
    # - p.image_url (string suelta)
    # - p.image_urls_json (string JSON tipo ["url1","url2"])
    urls: List[str] = []
    if p.image_url:
        urls.append(p.image_url)

    if p.image_urls_json:
        try:
            extra_urls = json.loads(p.image_urls_json)
            if isinstance(extra_urls, list):
                for u in extra_urls:
                    if isinstance(u, str) and u.strip():
                        urls.append(u)
        except Exception:
            pass

    # limpiamos duplicados manteniendo orden
    seen = set()
    clean_urls: List[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            clean_urls.append(u)

    return {
        "id": p.id,
        "title_marketing": marketing,
        "short_bullets": bullets_list,
        "price": p.price or 0,
        "currency": p.currency or "CLP",
        "image_urls": clean_urls,
    }


@router.get("/products/published")
def list_published_products():
    """
    Devuelve TODOS los productos con status='published'
    en un formato listo para la tienda pública (/).
    """
    with SessionLocal() as db:
        rows: List[Product] = (
            db.query(Product)
            .filter(Product.status == "published")
            .order_by(Product.id.desc())
            .all()
        )

    out: List[dict] = []
    for p in rows:
        out.append(_build_public_record(p))

    return out


@router.get("/products/{product_id}")
def get_product_detail(product_id: int):
    """
    Devuelve detalle de UN producto publicado.
    Útil si más adelante quieres página /producto/123.
    """
    with SessionLocal() as db:
        p: Optional[Product] = (
            db.query(Product)
            .filter(Product.id == product_id, Product.status == "published")
            .first()
        )

    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return _build_public_record(p)
