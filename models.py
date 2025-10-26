# models.py

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Float,
    Text,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db import Base  # <- importante: db.py NO debe importar Product arriba del archivo


# -------------------------------------------------
# Modelo Product
# Catálogo vendible, generado por IA, con estados draft/published/archived
# -------------------------------------------------
class Product(Base):
    __tablename__ = "products"

    # Identificador
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Nombre interno / base
    title: Mapped[str] = mapped_column(String(255), index=True)

    # slug público tipo "corrector-cervical-portatil"
    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)

    # Estado pipeline:
    #  - "draft"     : generado por IA o cargado, aún no público
    #  - "published" : visible al cliente final
    #  - "archived"  : oculto pero guardado
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)

    # Título vendedor visible en la ficha
    marketing_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Texto largo estilo landing / pitch
    description_long: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Bullets en formato string JSON
    # ej. '["Reduce tensión cervical","Úsalo frente al PC"]'
    bullets_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # FAQ en formato string JSON
    # ej. '[{"q":"Duele?","a":"No"},{"q":"Sirve sentado?","a":"Sí"}]'
    faq_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Nota/advertencia de uso
    risk_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Imagen principal
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Otras imágenes en formato string JSON (lista de URLs)
    image_urls_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Precio público
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Moneda ej. "CLP", "USD"
    currency: Mapped[Optional[str]] = mapped_column(String(8), default="CLP")

    # Score interno tipo "qué tan bueno lo ve la IA"
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # flag activo
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # sku proveedor
    supplier_sku: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # etiqueta de origen ("tiktok", "manual_seed_v1", etc.)
    source_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# -------------------------------------------------
# Modelo Order
# Pedido asociado a checkout (Stripe sandbox)
#
# Esto es lo que tu `routers/orders.py` está intentando importar.
# -------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ID de la sesión de pago en Stripe
    stripe_session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    # Estado del pago: "created", "pending", "paid", "canceled", etc.
    status: Mapped[Optional[str]] = mapped_column(
        String(50),
        default="created",
        index=True,
        nullable=True,
    )

    # Monto total
    # Nota: en CLP puedes guardar 12990 directamente
    #       en USD podrías guardar 1299 que significa $12.99
    amount_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Moneda ej "CLP", "USD"
    currency: Mapped[Optional[str]] = mapped_column(String(8), default="CLP")

    # Email del comprador (lo mostramos en /success)
    customer_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Producto comprado
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("products.id"),
        index=True,
        nullable=True,
    )

    # timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
