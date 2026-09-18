"""Capa de base de datos (SQLAlchemy 2 async)."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_async_engine(_settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Crea las tablas si no existen. Temporal en Fase 2; en Fase 3 pasa a Alembic."""
    from app import models  # noqa: F401  (registra los modelos en el metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
