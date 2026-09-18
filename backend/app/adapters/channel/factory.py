"""Selección del canal según la configuración."""
from app.adapters.channel.base import Channel
from app.adapters.channel.sim import SimChannel
from app.config import get_settings


def get_channel() -> Channel:
    provider = get_settings().channel_provider
    if provider == "whatsapp_cloud":
        # En Fase 5 se implementa WhatsAppCloudChannel (Meta). Por ahora, sim.
        return SimChannel()
    return SimChannel()
