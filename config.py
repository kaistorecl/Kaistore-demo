# config.py
#
# Centraliza configuración que viene de variables de entorno
# para que el resto del código pueda hacer: from config import settings
#
# IMPORTANTE:
#  - Ahora incluye ADMIN_SECRET (para los endpoints admin)
#  - CURRENCY, LOCALE, STRIPE_SECRET_KEY, etc. siguen existiendo
#
# OJO:
#  Render ya tiene las env vars cargadas (ADMIN_SECRET, CURRENCY, etc.)
#  así que esto va a leer esos valores en runtime.

import os
from pydantic import BaseModel


class Settings(BaseModel):
    # --- Admin token ---
    ADMIN_SECRET: str = os.getenv("ADMIN_SECRET", "CAMBIA_ESTE_TOKEN")

    # --- Detalles de negocio / localización ---
    CURRENCY: str = os.getenv("CURRENCY", "CLP")
    LOCALE: str = os.getenv("LOCALE", "es-CL")

    # --- URL pública del sitio (la home de la tienda) ---
    WEB_URL: str = os.getenv("WEB_URL", "http://localhost:8000")

    # --- Stripe ---
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Nota:
    # si más adelante agregas más cosas (DB_URL, etc.), las pones acá
    # y las lees igual con os.getenv(...)


# Instancia global para importar en todo el proyecto
settings = Settings()
