# models.py

from sqlalchemy import String, Float, Text, Boolean, Integer, DateTime, Column
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from db import Base


# ----------------- Productos (catálogo automatizable) -----------------

class Product(Base):
    __tablename__ = "products"

    # Identificador
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identidad / control interno
    # title: nombre base del producto (puede ser más "técnico")
    title: Mapped[str] = mapped_column(String(255), index=True)

    # slug: versión URL-amigable / identificador público corto
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # status: en qué etapa está el producto dentro del negocio
    # "draft"     -> generado por IA o cargado, aún no público
    # "published" -> visible en la tienda pública y API pública
    # "archived"  -> oculto pero guardado
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)

    # marketing_title: titular vendedor visible al cliente
    # ej. "Menos dolor de cuello en 15 minutos"
    marketing_title: Mapped[str] = mapped_column(String(255), nullable=True)

    # description_long: explicación larga estilo landing
    description_long: Mapped[str] = mapped_column(Text, nullable=True)

    # bullets_json: lista de bullets de beneficio (guardada como string JSON)
    # ej. '["Reduce tensión cervical","Úsalo frente al PC","Sin pastillas"]'
    bullets_json: Mapped[str] = mapped_column(Text, nullable=True)

    # faq_json: preguntas frecuentes en formato string JSON
    # ej. '[{"q":"¿Duele?","a":"No..."},{"q":"¿Sirve si trabajo 8h?","a":"Sí..."}]'
    faq_json: Mapped[str] = mapped_column(Text, nullable=True)

    # risk_note: advertencias básicas ("no lo uses mientras duermes", etc.)
    risk_note: Mapped[str] = mapped_column(Text, nullable=True)

    # Imagen principal (compatibilidad con tu implementación actual)
    image_url: Mapped[str] = mapped_column(String(512))

    # Varias imágenes opcionales (string JSON con lista de URLs)
    # ej. '["https://.../1.jpg","https://.../2.jpg"]'
    image_urls_json: Mapped[str] = mapped_column(Text, nullable=True)

    # Precio público que verá el cliente
    price: Mapped[float] = mapped_column(Float)

    # Moneda (por defecto CLP)
    currency: Mapped[str] = mapped_column(String(10), default="CLP")

    # score: ranking interno de prioridad / potencial
    # se puede usar como "qué tan prometedor lo vio la IA"
    score: Mapped[int] = mapped_column(Integer, default=0)

    # active: legacy flag que ya tenías.
    # Lo mantenemos para no romper nada que ya consuma esto.
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # supplier_sku: referencia proveedor / SKU externo
    supplier_sku: Mapped[str] = mapped_column(String(128), nullable=True)

    # source_label: de dónde viene este producto (para trazabilidad)
    # ej. "tiktok_trend", "manual_test", "ia_scout_v1"
    source_label: Mapped[str] = mapped_column(String(128), nullable=True)

    # timestamps
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, onupdate=func.now())


# ----------------- Ordenes (tu checkout / stripe / etc.) -----------------
# Nota: esto casi no lo tocamos, porque ya lo tienes andando

class Order(Base):
    __tablename__ = "orders2"

    id = Column(Integer, primary_key=True)

    # ID de sesión o de checkout (Stripe, etc.)
    session_id = Column(String, index=True, unique=True)

    # "created", "paid", "canceled", etc.
    status = Column(String, default="created")

    # correo del cliente (si lo capturas)
    email = Column(String, nullable=True)

    # moneda usada
    currency = Column(String, default="CLP")

    # monto total final
    amount = Column(Float, default=0.0)

    # timestamp
    created_at = Column(DateTime, server_default=func.now())
