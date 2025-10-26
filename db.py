from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime
from typing import List, Optional
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kaistore.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_published_products(db: Session) -> List["Product"]:
    from models import Product
    return db.query(Product).filter(Product.status == "published").all()

def get_product_by_id(db: Session, product_id: int) -> Optional["Product"]:
    from models import Product
    return db.query(Product).filter(Product.id == product_id).first()

def get_draft_products(db: Session) -> List["Product"]:
    from models import Product
    return db.query(Product).filter(Product.status == "draft").all()

def publish_product(db: Session, product_id: int, new_price: float) -> Optional["Product"]:
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
