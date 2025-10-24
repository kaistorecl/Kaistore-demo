from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db import SessionLocal
from models import Product
from schemas import ProductIn
from publishing import publish_product

router = APIRouter(prefix="/api/products", tags=["products"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.active == True).order_by(Product.id.desc()).limit(100).all()

@router.post("/")
def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    p = publish_product(db, payload)
    return p
