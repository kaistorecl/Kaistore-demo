from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

# Usa Postgres si defines DATABASE_URL. Si no, usa SQLite en /var/tmp (ruta escribible en Render)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////var/tmp/kaistore.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

# Dependency para FastAPI (si la usas en routers)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
