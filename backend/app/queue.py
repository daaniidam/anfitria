"""Cliente de la cola ARQ para encolar trabajo desde la API (webhook)."""
from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    """Pool de Redis compartido para encolar tareas (se crea una sola vez)."""
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


async def enqueue_inbound(
    property_id: int, guest_ref: str, text: str, external_id: str | None = None
) -> None:
    pool = await get_arq_pool()
    await pool.enqueue_job("process_inbound", property_id, guest_ref, text, external_id)
