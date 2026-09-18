"""Worker asíncrono (ARQ) para procesar mensajes entrantes y llamadas a la IA.

En la fase 1 solo expone una tarea de prueba (`ping`). En fases siguientes
aquí vivirá el pipeline: mensaje entrante -> recuperar conocimiento del piso
(RAG) -> generar borrador con la IA -> encolar para aprobación del anfitrión.
"""
from arq.connections import RedisSettings

from app.config import get_settings


async def ping(ctx: dict) -> str:
    return "pong"


class WorkerSettings:
    functions = [ping]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
