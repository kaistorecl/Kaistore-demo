# models.py
from sqlalchemy import String, Float, Text, Boolean, Integer, DateTime, Column
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from db import Base

# ----------------- Productos -----------------
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(512))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="CLP")
    score: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    supplier_sku: Mapped[str] = mapped_column(String(128), nullable=True)

# ----------------- Orden (simple) -----------------
# Usamos 'orders2' para evitar conflicto con una tabla 'orders' ya creada con otro esquema.
class Order(Base):
    __tablename__ = "orders2"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, index=True, unique=True)   # ID de sesión de Stripe (cs_test_...)
    status = Column(String, default="created")             # created | complete | canceled
    email = Column(String, nullable=True)
    currency = Column(String, default="CLP")
    amount = Column(Float, default=0.0)                    # monto en moneda normal (no centavos)
    created_at = Column(DateTime, server_default=func.now())
