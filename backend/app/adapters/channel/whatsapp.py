"""Canal de WhatsApp real (Meta WhatsApp Cloud API).

Envía mensajes salientes por la Graph API. La entrada llega por el webhook
(`app/api/whatsapp.py`). Requiere configurar en el entorno:
WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID (y para el webhook,
WHATSAPP_VERIFY_TOKEN y WHATSAPP_APP_SECRET).
"""
from __future__ import annotations

import httpx

from app.adapters.channel.base import Channel
from app.config import get_settings

GRAPH_API = "https://graph.facebook.com/v21.0"


class WhatsAppCloudChannel(Channel):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._settings = get_settings()
        self._client = client

    async def send(self, to: str, text: str) -> dict:
        settings = self._settings
        url = f"{GRAPH_API}/{settings.whatsapp_phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        client = self._client or httpx.AsyncClient(timeout=15)
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return {"status": "sent", "provider": "whatsapp_cloud", "response": response.json()}
        finally:
            if self._client is None:
                await client.aclose()
