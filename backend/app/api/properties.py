"""Pisos y su ficha de conocimiento."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.embeddings.factory import get_embedding_provider
from app.db import get_session
from app.deps import get_current_user
from app.models import KnowledgeItem, Property, User
from app.schemas import KnowledgeCreate, KnowledgeOut, PropertyCreate, PropertyOut

router = APIRouter(tags=["properties"])


async def get_owned_property(session: AsyncSession, property_id: int, user: User) -> Property:
    prop = await session.get(Property, property_id)
    if prop is None or prop.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Piso no encontrado")
    return prop


@router.post("/properties", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
async def create_property(
    data: PropertyCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Property:
    prop = Property(
        owner_id=user.id,
        name=data.name,
        address=data.address,
        default_language=data.default_language,
        auto_answer=data.auto_answer,
        whatsapp_phone_number_id=data.whatsapp_phone_number_id,
    )
    session.add(prop)
    await session.commit()
    await session.refresh(prop)
    return prop


@router.get("/properties", response_model=list[PropertyOut])
async def list_properties(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Property]:
    result = await session.execute(
        select(Property).where(Property.owner_id == user.id).order_by(Property.id)
    )
    return list(result.scalars().all())


@router.post(
    "/properties/{property_id}/knowledge",
    response_model=KnowledgeOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_knowledge(
    property_id: int,
    data: KnowledgeCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeItem:
    await get_owned_property(session, property_id, user)
    embedding = get_embedding_provider().embed([data.content])[0]
    item = KnowledgeItem(
        property_id=property_id,
        category=data.category,
        content=data.content,
        embedding=embedding,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/properties/{property_id}/knowledge", response_model=list[KnowledgeOut])
async def list_knowledge(
    property_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[KnowledgeItem]:
    await get_owned_property(session, property_id, user)
    result = await session.execute(
        select(KnowledgeItem)
        .where(KnowledgeItem.property_id == property_id)
        .order_by(KnowledgeItem.id)
    )
    return list(result.scalars().all())
