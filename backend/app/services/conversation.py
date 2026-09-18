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
from app.models import AuditLog, Conversation, Draft, Message, Property
from app.services.retrieval import retrieve


@dataclass
class InboundOutcome:
    conversation: Conversation
    inbound: Message
    draft: Draft
    auto_sent: bool


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
    session: AsyncSession, property: Property, guest_ref: str, text: str
) -> InboundOutcome:
    settings = get_settings()
    conversation = await _get_or_create_conversation(session, property.id, guest_ref)

    inbound = Message(
        conversation_id=conversation.id,
        direction="in",
        text=text,
        language=detect_language(text, property.default_language),
    )
    session.add(inbound)
    await session.flush()

    # RAG: recuperar los fragmentos más relevantes del piso para esta pregunta
    embedder = get_embedding_provider()
    query_embedding = embedder.embed([text])[0]
    hits = await retrieve(session, property.id, query_embedding)
    knowledge = [content for content, _ in hits]
    top_score = hits[0][1] if hits else 0.0

    ai = get_ai_provider()
    reply = await ai.generate_reply(
        AIContext(
            guest_text=text,
            property_name=property.name,
            knowledge=knowledge,
            default_language=property.default_language,
            retrieval_score=top_score,
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

    auto_sent = False
    if reply.confidence >= settings.auto_send_threshold:
        channel = get_channel()
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
            AuditLog(actor="ai", action="auto_sent", conversation_id=conversation.id)
        )
        auto_sent = True

    await session.commit()
    return InboundOutcome(
        conversation=conversation, inbound=inbound, draft=draft, auto_sent=auto_sent
    )
