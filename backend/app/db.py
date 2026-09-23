"""Capa de base de datos (SQLAlchemy 2 async)."""
from collections.abc import AsyncGenerator

from sqlalchemy import text
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
    """Prepara el esquema al arrancar.

    En desarrollo crea las tablas al vuelo (`create_all`) para arrancar sin pasos
    extra. En producción NO toca el esquema: se gestiona con Alembic
    (`alembic upgrade head`), la fuente de verdad de las migraciones.
    """
    from app import models  # noqa: F401  (registra los modelos en el metadata)

    if _settings.environment == "production":
        return

    async with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
