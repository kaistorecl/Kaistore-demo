# routers/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json

from db import get_db, get_published_products, get_product_by_id

router = APIRouter(
    prefix="/api/products",
    tags=["products-public"]
)


@router.get("/published")
def list_published_products(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Devuelve todos los productos publicados, en formato seguro
    para mostrar en la tienda (catálogo).
    """
    products = get_published_products(db)

    return [
        {
            "id": p.id,
            "title_marketing": p.marketing_title or p.title,
            "short_bullets": _safe_json_list(p.bullets_json),
            "price": p.price,
            "currency": p.currency,
            "image_urls": _safe_json_list(p.image_urls_json, fallback_single=p.image_url),
        }
        for p in products
    ]


@router.get("/{product_id}")
def get_product_detail(product_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Devuelve el detalle completo de un producto publicado.
    Esto alimenta la página de producto individual.
    """
    p = get_product_by_id(db, product_id)
    if not p or p.status != "published":
        raise HTTPException(status_code=404, detail="Producto no encontrado o no publicado")

    return {
        "id": p.id,
        "title_marketing": p.marketing_title or p.title,
        "description_long": p.description_long,
        "short_bullets": _safe_json_list(p.bullets_json),
        "faq": _safe_json_faq(p.faq_json),
        "risk_note": p.risk_note,
        "price": p.price,
        "currency": p.currency,
        "image_urls": _safe_json_list(p.image_urls_json, fallback_single=p.image_url),
    }


# ------------------------
# Helpers internos
# ------------------------

def _safe_json_list(raw: str, fallback_single: str = None):
    """
    Intenta parsear un string JSON que representa una lista de strings.
    Si falla o está vacío:
      - si fallback_single existe, devolvemos [fallback_single]
      - si no, devolvemos []
    """
    if not raw:
        return [fallback_single] if fallback_single else []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return [fallback_single] if fallback_single else []


def _safe_json_faq(raw: str):
    """
    Intenta parsear un string JSON de la forma:
    '[{"q":"...","a":"..."}, {"q":"...","a":"..."}]'
    Devuelve siempre una lista de dicts con q/a.
    """
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            cleaned = []
            for item in data:
                q = item.get("q") if isinstance(item, dict) else None
                a = item.get("a") if isinstance(item, dict) else None
                if q and a:
                    cleaned.append({"q": q, "a": a})
            return cleaned
        return []
    except Exception:
        return []
