"""Interfaz del canal de mensajería."""
from abc import ABC, abstractmethod


class Channel(ABC):
    """Envía un mensaje saliente a un huésped."""

    @abstractmethod
    async def send(self, to: str, text: str) -> dict:
        """Devuelve un dict con al menos {'status': ...}."""
        ...
