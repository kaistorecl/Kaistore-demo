import os
from pydantic import BaseModel

class Settings(BaseModel):
    CURRENCY: str = os.getenv("CURRENCY", "CLP")
    LOCALE: str = os.getenv("LOCALE", "es-CL")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")

settings = Settings()
