"""Selección del proveedor de IA según la configuración."""
from app.adapters.ai.base import AIProvider
from app.adapters.ai.mock import MockAI
from app.config import get_settings


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "anthropic" and settings.anthropic_api_key:
        from app.adapters.ai.anthropic_ai import AnthropicAI

        return AnthropicAI()
    # Por defecto (o si falta la clave): mock determinista, sin coste.
    return MockAI()
