"""Configuración de la aplicación (pydantic-settings)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AnfitrIA"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://anfitria:anfitria@db:5432/anfitria"
    redis_url: str = "redis://redis:6379/0"

    # Seguridad / JWT (cambiar secret_key en producción vía entorno)
    secret_key: str = "dev-insecure-change-me-in-production-please-32b+"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 14  # 14 días
    # El token va en cookie httpOnly (no accesible por JS → resiste XSS).
    cookie_secure: bool = False  # True en producción (HTTPS)
    cookie_samesite: str = "lax"

    # Límite de peticiones (fuerza bruta / spam). Se desactiva en los tests.
    rate_limit_enabled: bool = True
    # Backend del rate limit: por defecto en memoria (por proceso). En producción
    # con varias réplicas, apunta a Redis (p. ej. redis://redis:6379/1) para un
    # límite global compartido.
    rate_limit_storage_uri: str | None = None

    # Si True, el webhook de WhatsApp encola el trabajo pesado (IA) en el worker
    # ARQ y responde al instante; si False, procesa en línea (demo/tests).
    process_async: bool = False

    # Umbral de confianza (0-1) para que la IA responda sola. Por debajo, escala
    # al anfitrión (y el huésped recibe igual un mensaje de espera inmediato).
    auto_answer_threshold: float = 0.55

    # IA: "mock" (sin clave, por defecto) | "anthropic" (Claude real)
    ai_provider: str = "mock"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"

    # Canal: "sim" (WhatsApp simulado) | "whatsapp_cloud" (Meta Cloud API)
    channel_provider: str = "sim"
    whatsapp_verify_token: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_app_secret: str | None = None

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
