from sqlalchemy import String, Float, Text, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from db import Base

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

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="CREATED")  # CREATED, PAID
    total: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="CLP")
    customer_email: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    order: Mapped[Order] = relationship("Order", back_populates="items")
    
# --- NUEVO: modelo simple para registrar sesiones de Checkout ---
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime

class CheckoutSession(Base):
    __tablename__ = "checkout_sessions"

    # id de la sesión de Stripe (ej: cs_test_123)
    id = Column(String, primary_key=True)
    amount_total = Column(Integer, default=0)      # en centavos
    currency = Column(String(10), default="CLP")
    customer_email = Column(String(255), nullable=True)
    status = Column(String(50), default="CREATED")
    created_at = Column(DateTime, default=datetime.utcnow)
# ---- Orders ----
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func

