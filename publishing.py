from slugify import slugify
from sqlalchemy.orm import Session
from ..models import Product
from ..schemas import ProductIn

def publish_product(db: Session, payload: ProductIn) -> Product:
    slug = slugify(payload.title)
    existing = db.query(Product).filter(Product.slug == slug).first()
    if existing:
        return existing
    p = Product(
        title=payload.title,
        slug=slug,
        description=payload.description,
        image_url=payload.image_url,
        price=payload.price,
        currency=payload.currency,
        score=payload.score,
        supplier_sku=payload.supplier_sku,
    )
    db.add(p); db.commit(); db.refresh(p)
    return p
