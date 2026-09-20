"""Tests del proveedor de IA con Claude, usando un cliente falso (sin clave real)."""
from app.adapters.ai.anthropic_ai import AnthropicAI
from app.adapters.ai.base import AIContext


class _Block:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _Response:
    def __init__(self, text: str):
        self.content = [_Block(text)]


class _Messages:
    def __init__(self, text: str):
        self._text = text

    async def create(self, **kwargs):
        return _Response(self._text)


class _FakeClient:
    def __init__(self, text: str):
        self.messages = _Messages(text)


async def test_anthropic_answers_when_it_can():
    client = _FakeClient('{"can_answer": true, "reply": "El check-in es a las 15:00.", "language": "es"}')
    ai = AnthropicAI(client=client)
    reply = await ai.generate_reply(
        AIContext(
            guest_text="¿a qué hora puedo entrar?",
            property_name="Piso",
            all_knowledge=["Check-in a partir de las 15:00"],
        )
    )
    assert reply.text == "El check-in es a las 15:00."
    assert reply.confidence >= 0.55
    assert reply.language == "es"


async def test_anthropic_escalates_when_it_cannot():
    client = _FakeClient('{"can_answer": false, "reply": "Lo confirmo con el anfitrión.", "language": "es"}')
    ai = AnthropicAI(client=client)
    reply = await ai.generate_reply(
        AIContext(guest_text="¿hay piscina?", property_name="Piso", all_knowledge=["wifi: 1234"])
    )
    assert reply.confidence < 0.55


async def test_anthropic_degrades_safely_on_error():
    class _Boom:
        async def create(self, **kwargs):
            raise RuntimeError("network down")

    class _BrokenClient:
        messages = _Boom()

    ai = AnthropicAI(client=_BrokenClient())
    reply = await ai.generate_reply(AIContext(guest_text="hi there", property_name="Flat"))
    assert reply.confidence < 0.55
    assert reply.text  # devuelve un mensaje de espera, no rompe la conversación
