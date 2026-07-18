from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models
from app.config.settings import settings

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

def get_session():
    return SessionLocal()
