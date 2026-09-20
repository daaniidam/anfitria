"""Selección del canal según la configuración."""
from app.adapters.channel.base import Channel
from app.adapters.channel.sim import SimChannel
from app.config import get_settings


def get_channel() -> Channel:
    settings = get_settings()
    if settings.channel_provider == "whatsapp_cloud" and settings.whatsapp_access_token:
        from app.adapters.channel.whatsapp import WhatsAppCloudChannel

        return WhatsAppCloudChannel()
    # Por defecto (o sin credenciales): canal simulado.
    return SimChannel()
