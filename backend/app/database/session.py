from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models
from app.config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT_SECONDS,
    pool_recycle=settings.DATABASE_POOL_RECYCLE_SECONDS,
    connect_args=settings.database_connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_session():
    return SessionLocal()


def dispose_engine() -> None:
    """Close all pooled connections during application shutdown."""
    engine.dispose(close=True)
