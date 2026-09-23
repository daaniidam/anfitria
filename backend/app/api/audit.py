"""Registro de auditoría del anfitrión: qué hizo la IA y el anfitrión, y cuándo.

Hace visible la trazabilidad — el principio de "IA supervisada, no caja negra".
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import AuditLog, Conversation, Property, User
from app.schemas import AuditLogOut

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=list[AuditLogOut])
async def list_audit(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AuditLog]:
    prop_ids = select(Property.id).where(Property.owner_id == user.id)
    conv_ids = select(Conversation.id).where(Conversation.property_id.in_(prop_ids))
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.conversation_id.in_(conv_ids))
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
