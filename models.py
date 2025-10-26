# models.py

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Text, Boolean, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db import Base  # Importamos Base desde db.py (esto está OK, no genera circular si db no importa Product arriba)


class Product(Base):
    __tablename__ = "products"

    # Identificador
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identidad / control interno
    # title: nombre base del producto
    title: Mapped[str] = mapped_column(String(255), index=True)

    # slug: URL-amigable / identificador público corto
    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)

    # status:
    #  "draft"     -> generado por IA o cargado, aún no publicado
    #  "published" -> visible en tienda y API pública
    #  "archived"  -> oculto
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)

    # marketing_title: titular vendedor visible al cliente ("Menos dolor de cuello en 15 minutos")
    marketing_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # description_long: explicación larga estilo landing / ficha de venta
    description_long: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # bullets_json: lista de bullets de beneficio en formato string JSON
    # ej. '["Reduce tensión cervical", "Úsalo frente al PC", "Sin pastillas"]'
    bullets_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # faq_json: preguntas frecuentes en formato string JSON
    # ej. '[{"q":"Duele?","a":"No"}, {"q":"Sirve si trabajo sentado?","a":"Sí"}]'
    faq_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # risk_note: advertencias tipo "no usar mientras duermes"
    risk_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # imagen principal
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # image_urls_json: lista de urls adicionales en formato string JSON
    image_urls_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Precio público + moneda
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(8), default="CLP")

    # Señal interna (score IA, prioridad, etc.)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Activo / visible
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # supplier_sku: referencia proveedor
    supplier_sku: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # source_label: de dónde vino este candidato (ej. "tiktok", "aliexpress", "manual_seed_v1")
    source_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps (creado / actualizado)
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
