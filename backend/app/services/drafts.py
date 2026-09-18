"""Servicio de aprobación de borradores."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.channel.factory import get_channel
from app.models import AuditLog, Conversation, Draft, Message


async def approve_draft(
    session: AsyncSession,
    draft: Draft,
    conversation: Conversation,
    edited_text: str | None = None,
) -> Message:
    text = (edited_text if edited_text is not None else draft.text).strip()
    edited = edited_text is not None and text != draft.text.strip()

    channel = get_channel()
    await channel.send(conversation.guest_ref, text)

    outbound = Message(
        conversation_id=conversation.id,
        direction="out",
        text=text,
        language=draft.language,
    )
    session.add(outbound)
    draft.status = "sent"
    session.add(
        AuditLog(
            actor="host",
            action="edited_and_sent" if edited else "approved_and_sent",
            conversation_id=conversation.id,
        )
    )
    await session.commit()
    return outbound
