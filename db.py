# db.py

import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Creamos Base primero
Base = declarative_base()

# -------------------------------------------------------------------
# CONFIG DB
# -------------------------------------------------------------------
# En Render normalmente tienes DATABASE_URL (Postgres).
# Si no existe, usamos sqlite local para desarrollo.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kaistore.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Importar Product después de definir Base/engine para evitar ciclo
from models import Product  # noqa: E402


# -------------------------------------------------------------------
# Dependency para FastAPI (inyectar sesión db)
# -------------------------------------------------------------------
def get_db():
    """
    Uso en endpoints:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# CRUD helpers Product
# -------------------------------------------------------------------

def get_published_products(db: Session) -> List[Product]:
    """
    Todos los productos con status='published'.
    Estos son los que salen en la tienda pública.
    """
    return db.query(Product).filter(Product.status == "published").all()


def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    """
    Buscar un producto por id.
    Sirve para detalle de producto o para el checkout.
    """
    return db.query(Product).filter(Product.id == product_id).first()


def get_draft_products(db: Session) -> List[Product]:
    """
    Productos en estado 'draft' (aún no publicados).
    El panel admin muestra esto para que tú decidas qué publicar.
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


def create_demo_draft(db: Session) -> Product:
    """
    Inserta un producto DEMO como 'draft'.
    Simula lo que generaría la IA.
    """
    import json

    demo = Product(
        title="Corrector cervical portátil",
        slug="corrector-cervical-portatil",
        status="draft",
        marketing_title="Menos dolor de cuello en 15 minutos frente al PC",
        description_long=(
            "¿Terminas el día con el cuello duro y tensión en la zona cervical? "
            "Este soporte ajustable te ayuda a mantener una postura más cómoda "
            "mientras trabajas o descansas, sin pastillas ni cremas."
        ),
        bullets_json=json.dumps([
            "Reduce tensión cervical después de horas frente al PC",
            "Úsalo sentado mientras trabajas",
            "Sin pastillas ni cremas",
            "Ajustable y cómodo"
        ]),
        faq_json=json.dumps([
            {"q": "¿Duele usarlo?", "a": "No debería doler. Debe sentirse firme pero cómodo."},
            {"q": "¿Sirve si trabajo 8 horas sentado?", "a": "Sí, está pensado para gente frente a pantalla."},
            {"q": "¿Cuánto demora el envío?", "a": "Promedio 2-4 días hábiles según tu zona."}
        ]),
        risk_note="No apretar demasiado. No usar mientras duermes.",
        image_url="https://example.com/cervical-main.jpg",
        image_urls_json=json.dumps([
            "https://example.com/cervical-main.jpg",
            "https://example.com/cervical-side.jpg"
        ]),
        price=12990,
        currency="CLP",
        score=90,
        active=True,
        supplier_sku="cx-neck-relief-v1",
        source_label="manual_seed_v1",
    )

    db.add(demo)
    db.commit()
    db.refresh(demo)
    return demo


def get_all_products(db: Session) -> List[Product]:
    """
    DEBUG: trae TODOS los productos sin filtrar.
    Sirve para diagnosticar por qué drafts/published salen vacíos.
    """
    return db.query(Product).all()
