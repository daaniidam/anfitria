"""Servicio de conversación: procesa un mensaje entrante y genera el borrador."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.ai.base import AIContext
from app.adapters.ai.factory import get_ai_provider
from app.adapters.ai.mock import detect_language
from app.adapters.channel.factory import get_channel
from app.adapters.embeddings.factory import get_embedding_provider
from app.config import get_settings
from app.models import (
    AuditLog,
    Conversation,
    Draft,
    KnowledgeItem,
    Message,
    Notification,
    Property,
)
from app.services.reservations import build_stay_context, find_reservation
from app.services.retrieval import retrieve, scope_clause

# Mensaje de espera que recibe el huésped al instante cuando se escala al anfitrión.
HOLDING = {
    "es": "¡Hola! Lo confirmo con el anfitrión y te respondo enseguida. 🙌",
    "en": "Hi! Let me check this with the host and get right back to you. 🙌",
    "fr": "Bonjour ! Je vérifie avec l'hôte et je vous réponds tout de suite. 🙌",
    "de": "Hallo! Ich kläre das mit dem Gastgeber und melde mich gleich. 🙌",
    "it": "Ciao! Lo verifico con l'host e ti rispondo subito. 🙌",
}


@dataclass
class InboundOutcome:
    conversation: Conversation
    inbound: Message
    draft: Draft | None
    answered: bool
    duplicate: bool = False  # True si el mensaje ya se había procesado (reintento del webhook)


async def _find_by_external_id(session: AsyncSession, external_id: str) -> Message | None:
    result = await session.execute(select(Message).where(Message.external_id == external_id))
    return result.scalar_one_or_none()


async def _get_or_create_conversation(
    session: AsyncSession, property_id: int, guest_ref: str
) -> Conversation:
    result = await session.execute(
        select(Conversation).where(
            Conversation.property_id == property_id,
            Conversation.guest_ref == guest_ref,
            Conversation.channel == "sim",
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        conversation = Conversation(property_id=property_id, guest_ref=guest_ref, channel="sim")
        session.add(conversation)
        await session.flush()
    return conversation


async def handle_inbound(
    session: AsyncSession,
    property: Property,
    guest_ref: str,
    text: str,
    external_id: str | None = None,
) -> InboundOutcome:
    settings = get_settings()

    # Idempotencia: si este mensaje del canal ya se procesó (reintento del webhook),
    # no lo procesamos de nuevo — evita responder dos veces al huésped.
    if external_id is not None:
        existing = await _find_by_external_id(session, external_id)
        if existing is not None:
            conversation = await session.get(Conversation, existing.conversation_id)
            return InboundOutcome(
                conversation=conversation,
                inbound=existing,
                draft=existing.draft,
                answered=False,
                duplicate=True,
            )

    conversation = await _get_or_create_conversation(session, property.id, guest_ref)

    inbound = Message(
        conversation_id=conversation.id,
        direction="in",
        text=text,
        language=detect_language(text, property.default_language),
        external_id=external_id,
    )
    session.add(inbound)
    await session.flush()

    # Handoff en vivo: una persona ha tomado el control; la IA no responde, solo avisa.
    if conversation.handoff:
        session.add(
            AuditLog(actor="ai", action="handoff_inbound", conversation_id=conversation.id)
        )
        session.add(
            Notification(
                owner_id=property.owner_id,
                org_id=property.org_id,
                conversation_id=conversation.id,
                kind="handoff",
                message=f"{property.name}: nuevo mensaje (atención en vivo)",
            )
        )
        await session.commit()
        return InboundOutcome(
            conversation=conversation, inbound=inbound, draft=None, answered=False
        )

    # RAG: recuperar los fragmentos más relevantes (para el mock y como señal de confianza)
    embedder = get_embedding_provider()
    query_embedding = embedder.embed([text])[0]
    hits = await retrieve(session, property.id, query_embedding, building_id=property.building_id)
    knowledge = [content for content, _ in hits]
    top_score = hits[0][1] if hits else 0.0

    # Todo el conocimiento del piso + el compartido de su edificio (los modelos que razonan
    # semánticamente, como Claude, eligen ellos mismos lo relevante).
    all_rows = await session.execute(
        select(KnowledgeItem.content).where(scope_clause(property.id, property.building_id))
    )
    all_knowledge = [row[0] for row in all_rows.all()]

    # Contexto de la reserva: en qué fase de la estancia está el huésped.
    reservation = await find_reservation(session, property.id, guest_ref)
    stay_context = build_stay_context(reservation) if reservation is not None else None

    ai = get_ai_provider()
    reply = await ai.generate_reply(
        AIContext(
            guest_text=text,
            property_name=property.name,
            knowledge=knowledge,
            all_knowledge=all_knowledge,
            default_language=property.default_language,
            retrieval_score=top_score,
            stay_context=stay_context,
        )
    )

    draft = Draft(
        inbound_message_id=inbound.id,
        text=reply.text,
        language=reply.language,
        confidence=reply.confidence,
        model=reply.model,
        status="pending",
    )
    session.add(draft)
    session.add(
        AuditLog(
            actor="ai",
            action="draft_generated",
            conversation_id=conversation.id,
            detail=f"confidence={reply.confidence:.2f} model={reply.model}",
        )
    )
    await session.flush()

    channel = get_channel()
    answered = property.auto_answer and reply.confidence >= settings.auto_answer_threshold

    if answered:
        # La IA responde sola al huésped.
        await channel.send(conversation.guest_ref, draft.text)
        session.add(
            Message(
                conversation_id=conversation.id,
                direction="out",
                text=draft.text,
                language=draft.language,
            )
        )
        draft.status = "sent"
        session.add(
            AuditLog(actor="ai", action="auto_answered", conversation_id=conversation.id)
        )
    else:
        # Escalada: el huésped recibe un mensaje de espera y el anfitrión responde luego.
        holding = HOLDING.get(reply.language, HOLDING["es"])
        await channel.send(conversation.guest_ref, holding)
        session.add(
            Message(
                conversation_id=conversation.id,
                direction="out",
                text=holding,
                language=reply.language,
            )
        )
        # El borrador queda "pending": es la escalada para el anfitrión.
        session.add(
            AuditLog(actor="ai", action="escalated", conversation_id=conversation.id)
        )
        # Aviso al anfitrión para que no dependa de estar mirando el panel.
        preview = text if len(text) <= 80 else text[:77] + "…"
        session.add(
            Notification(
                owner_id=property.owner_id,
                org_id=property.org_id,
                conversation_id=conversation.id,
                kind="escalation",
                message=f'{property.name}: "{preview}"',
            )
        )

    await session.commit()
    return InboundOutcome(
        conversation=conversation, inbound=inbound, draft=draft, answered=answered
    )
