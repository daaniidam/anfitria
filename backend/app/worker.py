"""Worker asíncrono (ARQ): procesa los mensajes entrantes fuera del webhook.

El webhook de WhatsApp encola aquí el trabajo pesado (recuperar conocimiento +
llamar a la IA) y responde a Meta al instante. Así el webhook no se bloquea con
la latencia de la IA (que provocaría timeouts y reintentos).

Se activa con `PROCESS_ASYNC=true`; con `false` (demo/tests) el procesamiento se
hace en línea en el propio webhook.
"""
from arq.connections import RedisSettings

from app.config import get_settings
from app.db import SessionLocal
from app.models import Property
from app.services.conversation import handle_inbound


async def ping(ctx: dict) -> str:
    return "pong"


async def process_inbound(
    ctx: dict,
    property_id: int,
    guest_ref: str,
    text: str,
    external_id: str | None = None,
) -> str:
    """Tarea encolada: ejecuta el pipeline de conserje para un mensaje entrante."""
    async with SessionLocal() as session:
        property = await session.get(Property, property_id)
        if property is None:
            return "property_not_found"
        outcome = await handle_inbound(session, property, guest_ref, text, external_id=external_id)
        if outcome.duplicate:
            return "duplicate"
        return "answered" if outcome.answered else "escalated"


class WorkerSettings:
    functions = [ping, process_inbound]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
