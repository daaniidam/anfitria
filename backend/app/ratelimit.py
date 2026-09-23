"""Limitador de peticiones (slowapi) compartido por la app y las rutas.

Protege endpoints sensibles (login, entrada de mensajes) frente a fuerza bruta y
spam. Se desactiva en los tests con `app.state.limiter.enabled = False`.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_settings = get_settings()

# Con `rate_limit_storage_uri` (Redis) el límite es global entre réplicas; sin él,
# en memoria por proceso (suficiente en una sola instancia / desarrollo).
_limiter_kwargs: dict = {
    "key_func": get_remote_address,
    "enabled": _settings.rate_limit_enabled,
    "default_limits": [],
}
if _settings.rate_limit_storage_uri:
    _limiter_kwargs["storage_uri"] = _settings.rate_limit_storage_uri

limiter = Limiter(**_limiter_kwargs)
