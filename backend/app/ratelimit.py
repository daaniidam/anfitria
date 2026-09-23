"""Limitador de peticiones (slowapi) compartido por la app y las rutas.

Protege endpoints sensibles (login, entrada de mensajes) frente a fuerza bruta y
spam. Se desactiva en los tests con `app.state.limiter.enabled = False`.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    enabled=get_settings().rate_limit_enabled,
    default_limits=[],
)
