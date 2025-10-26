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

from db import Base  # <- importante: db.py NO debe importar Product arriba del archivo,
                     # así evitamos el import circular


# -------------------------------------------------
# Modelo Product
# Catálogo vendible, generado por IA, con estados draft/published/archived
# -------------------------------------------------
class Product(Base):
    __tablename__ = "products"

    # Identificador
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Nombre base interno / técnico
    title: Mapped[str] = mapped_column(String(255), index=True)

    # slug público tipo "corrector-cervical-portatil"
    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)

    # Estado del producto en el pipeline:
    #  - "draft"     : generado por IA o cargado, aún no público
    #  - "published" : visible al cliente final
    #  - "archived"  : oculto pero guardado
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)

    # Título vendedor visible en la ficha
    marketing_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Texto largo estilo landing / pitch
    description_long: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Bullets en formato JSON string
    # ej. '["Reduce tensión cervical","Úsalo frente al PC"]'
    bullets_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # FAQ en formato JSON string
    # ej. '[{"q":"Duele?","a":"No"},{"q":"Sirve sentado?","a":"Sí"}]'
    faq_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Nota de riesgo/uso
    risk_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Imagen principal
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Otras imágenes en formato JSON string (lista de URLs)
    image_urls_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Precio público
    # NOTA: en tu frontend asumimos que si la moneda NO es de decimales (CLP),
    #       price ya viene como entero final (ej 12990).
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    currency: Mapped[Optional[str]] = mapped_column(String(8), default="CLP")

    # Score interno de priorización (ej. 90 = hype alto / viral / buen margen)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Flag rápido de "activo"
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # SKU proveedor o referencia proveedor
    supplier_sku: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Etiqueta de origen ("tiktok", "aliexpress", "manual_seed_v1", etc.)
    source_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
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
# Pedido / intento de compra asociado a Stripe checkout (sandbox)
#
# Nota: estoy asumiendo campos comunes que tu router de pagos suele usar:
# - stripe_session_id: el id de sesión devuelto por Stripe
# - status: "open", "paid", "canceled", etc.
# - amount_total y currency: lo que mostramos en /success
# - customer_email: el correo del comprador
# - product_id: qué producto quiso comprar
#
# Esto es lo mínimo para que "from models import Product, Order"
# en tu routers/orders.py NO reviente.
# -------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ID de la sesión de pago (Stripe Checkout Session ID)
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

    # Monto total de la orden
    # IMPORTANTE:
    # - En monedas sin decimales (ej CLP) podrías guardar 12990
    # - En monedas con decimales (ej USD) podrías guardar 1299 que significa $12.99
    amount_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Moneda ej "CLP", "USD"
    currency: Mapped[Optional[str]] = mapped_column(String(8), default="CLP")

    # Email del comprador (lo mostramos en /success)
    customer_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Producto asociado a la compra
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("products.id"),
        index=True,
        nullable=True,
    )

    # Timestamps
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
