from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models import Product  # asegúrate que Product tiene estas columnas

router = APIRouter(
    prefix="/api/products",
    tags=["products-public"],
)


@router.get("/published")
def list_published_products(db: Session = Depends(get_db)):
    """
    Devuelve todos los productos publicados, en formato seguro para mostrar en la tienda (catálogo).
    """
    rows = (
        db.query(Product)
        .filter(Product.status == "published")
        .order_by(Product.id.desc())
        .all()
    )

    out = []
    for p in rows:
        out.append({
            "id": p.id,
            "title_marketing": getattr(p, "title_marketing", None),
            "short_bullets": getattr(p, "short_bullets", None),
            "price": p.price,
            "currency": p.currency,
            "image_urls": getattr(p, "image_urls", None),
        })
    return out


@router.get("/{product_id}")
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    """
    Detalle de un producto publicado (para página individual futura).
    """
    p = (
        db.query(Product)
        .filter(Product.id == product_id, Product.status == "published")
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return {
        "id": p.id,
        "title_marketing": getattr(p, "title_marketing", None),
        "short_bullets": getattr(p, "short_bullets", None),
        "price": p.price,
        "currency": p.currency,
        "image_urls": getattr(p, "image_urls", None),
    }
