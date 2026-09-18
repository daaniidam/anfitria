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
    access_token_expire_minutes: int = 60 * 24

    # Umbral de confianza para auto-envío (0-1); por encima, la IA puede enviar sola
    auto_send_threshold: float = 0.85

    # IA: "mock" (sin clave, por defecto) | "anthropic" (Claude real)
    ai_provider: str = "mock"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

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
