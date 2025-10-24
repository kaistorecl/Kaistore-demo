import os
from pydantic import BaseModel

class Settings(BaseModel):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./demo.db")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    CURRENCY: str = os.getenv("CURRENCY", "CLP")
    LOCALE: str = os.getenv("LOCALE", "es-CL")

settings = Settings()
