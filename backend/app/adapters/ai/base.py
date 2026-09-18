"""Interfaz del proveedor de IA."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AIContext:
    guest_text: str
    property_name: str
    knowledge: list[str] = field(default_factory=list)
    default_language: str = "es"
    retrieval_score: float = 0.0


@dataclass
class GeneratedReply:
    text: str
    language: str
    confidence: float
    model: str


class AIProvider(ABC):
    """Genera un borrador de respuesta para un mensaje de huésped."""

    @abstractmethod
    async def generate_reply(self, context: AIContext) -> GeneratedReply: ...
