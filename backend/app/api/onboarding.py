"""Estado de arranque (onboarding): qué pasos ha completado el anfitrión.

Guía al anfitrión nuevo para que no se quede en un panel vacío: crea un piso,
completa la ficha, y prueba con un huésped. Los pasos se detectan de los datos
reales, así que se marcan solos.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import Conversation, KnowledgeItem, Property, User
from app.schemas import OnboardingStatus

router = APIRouter(tags=["onboarding"])


async def _exists(session: AsyncSession, stmt: Select) -> bool:
    result = await session.execute(select(func.count()).select_from(stmt.subquery()))
    return int(result.scalar_one() or 0) > 0


@router.get("/onboarding", response_model=OnboardingStatus)
async def onboarding_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OnboardingStatus:
    prop_ids = select(Property.id).where(Property.org_id == user.org_id)
    return OnboardingStatus(
        has_property=await _exists(session, prop_ids),
        has_knowledge=await _exists(
            session,
            select(KnowledgeItem.id).where(KnowledgeItem.property_id.in_(prop_ids)),
        ),
        has_whatsapp=await _exists(
            session,
            select(Property.id).where(
                Property.org_id == user.org_id,
                Property.whatsapp_phone_number_id.isnot(None),
            ),
        ),
        has_conversation=await _exists(
            session, select(Conversation.id).where(Conversation.property_id.in_(prop_ids))
        ),
    )
