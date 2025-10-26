# db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import List, Optional
from datetime import datetime
import os

# Importa Product DESPUÉS de definir Base (evitamos ciclo raro)
Base = declarative_base()

# -------------------------------------------------------------------
# CONFIG DB
# -------------------------------------------------------------------
# Render normalmente te da DATABASE_URL en variables de entorno.
# Si no existe, usamos sqlite local (para que siga funcionando localmente).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kaistore.db")

# Si es sqlite, necesitamos connect_args especiales.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Importar Product después de Base para evitar import circular
from models import Product  # noqa: E402


# -------------------------------------------------------------------
# Dependency de sesión (FastAPI Depends)
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


def create_demo_draft(db: Session) -> Product:
    """
    Inserta un producto DEMO en estado 'draft'.
    Este producto simula lo que haría la IA.
    Devuelve el Product creado.
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
