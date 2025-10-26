# db.py

import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# -------------------------------------------------------------------
# CONFIG DB
# -------------------------------------------------------------------

# Render normalmente te setea DATABASE_URL en variables de entorno (Postgres).
# Localmente podemos usar sqlite.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kaistore.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# -------------------------------------------------------------------
# FastAPI dependency para obtener sesión DB en endpoints
# -------------------------------------------------------------------
def get_db():
    """
    Uso en routers FastAPI:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# CRUD helpers de Product
# IMPORTANTE: acá NO importamos Product arriba para evitar el import circular.
# Lo importamos adentro de cada función.
# -------------------------------------------------------------------

def get_published_products(db: Session) -> List["Product"]:
    """
    Retorna todos los productos con status = 'published'
    (estos se muestran en la tienda pública).
    """
    from models import Product
    return db.query(Product).filter(Product.status == "published").all()


def get_product_by_id(db: Session, product_id: int) -> Optional["Product"]:
    """
    Trae un producto por ID.
    Sirve para la página de detalle y para soportar checkout.
    """
    from models import Product
    return db.query(Product).filter(Product.id == product_id).first()


def get_draft_products(db: Session) -> List["Product"]:
    """
    Retorna todos los productos con status = 'draft'
    (estos son los que propone la IA o subes tú pero sin publicar aún).
    """
    from models import Product
    return db.query(Product).filter(Product.status == "draft").all()


def publish_product(db: Session, product_id: int, new_price: float) -> Optional["Product"]:
    """
    Cambia un producto de 'draft' -> 'published' y actualiza su precio.
    Lo usa el panel admin.
    """
    from models import Product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None

    product.status = "published"
    product.price = new_price
    product.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(product)
    return product
