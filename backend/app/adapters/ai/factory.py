"""Selección del proveedor de IA según la configuración."""
from app.adapters.ai.base import AIProvider
from app.adapters.ai.mock import MockAI
from app.config import get_settings


def get_ai_provider() -> AIProvider:
    provider = get_settings().ai_provider
    if provider == "anthropic":
        # En Fase 4 se implementa AnthropicAI (Claude). Por ahora, mock como red de seguridad.
        return MockAI()
    return MockAI()
