# db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import List, Optional
from datetime import datetime

from models import Product  # importante: importa el Product que acabas de actualizar

# -------------------------------------------------------------------
# CONFIG DB
# -------------------------------------------------------------------
# Ajusta esto si en config.py ya tenías DATABASE_URL. Si lo tienes,
# puedes importar DATABASE_URL desde config.py en lugar de hardcodearlo.

# Ejemplo:
# from config import DATABASE_URL
# engine = create_engine(DATABASE_URL)

# Si aún no tienes DATABASE_URL centralizado, déjalo así por ahora
# y luego lo cambias a lo que Render esté usando (Postgres, etc.):

DATABASE_URL = "sqlite:///./kaistore.db"  # <- placeholder local. En Render será postgresql://...

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# -------------------------------------------------------------------
# UTILS DE SESIÓN (FastAPI style dependency)
# -------------------------------------------------------------------
def get_db():
    """
    Dependency para inyectar sesión DB en los endpoints.
    Uso en routers:
    db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# CRUD helpers para Product
# -------------------------------------------------------------------

def get_published_products(db: Session) -> List[Product]:
    """
    Retorna todos los productos con status = 'published'.
    Estos son los que deben mostrarse en la tienda pública.
    """
    return db.query(Product).filter(Product.status == "published").all()


def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    """
    Trae un producto por id.
    Sirve para página de detalle y para el chatbot.
    """
    return db.query(Product).filter(Product.id == product_id).first()


def get_draft_products(db: Session) -> List[Product]:
    """
    Retorna productos en estado 'draft', que la IA (o tú) crearon
    pero que aún no están publicados al público.
    Esto se mostrará en /dashboard para que tú los apruebes.
    """
    return db.query(Product).filter(Product.status == "draft").all()


def publish_product(db: Session, product_id: int, new_price: float) -> Optional[Product]:
    """
    Cambia un producto desde draft -> published y ajusta precio.
    Esto es lo que hace el botón "Publicar".
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None

    product.status = "published"
    product.price = new_price
    product.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(product)
    return product
