"""Canal simulado: no llama a ningún servicio externo.

El mensaje saliente se persiste como `Message` en la conversación (lo hace el
servicio) y el chat de huésped simulado lo lee de la API. Aquí solo confirmamos
la "entrega".
"""
from app.adapters.channel.base import Channel


class SimChannel(Channel):
    async def send(self, to: str, text: str) -> dict:
        return {"status": "sent", "provider": "sim", "to": to}
