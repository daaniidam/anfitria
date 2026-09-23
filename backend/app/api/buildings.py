"""Edificios / grupos de pisos con conocimiento compartido."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.embeddings.factory import get_embedding_provider
from app.db import get_session
from app.deps import get_current_user, require_owner
from app.models import Building, KnowledgeItem, User
from app.schemas import (
    BuildingCreate,
    BuildingOut,
    KnowledgeCreate,
    KnowledgeOut,
    KnowledgeUpdate,
)

router = APIRouter(tags=["buildings"])


async def get_owned_building(session: AsyncSession, building_id: int, user: User) -> Building:
    building = await session.get(Building, building_id)
    if building is None or building.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")
    return building


async def _owned_building_knowledge(
    session: AsyncSession, building_id: int, item_id: int, user: User
) -> KnowledgeItem:
    await get_owned_building(session, building_id, user)
    item = await session.get(KnowledgeItem, item_id)
    if item is None or item.building_id != building_id:
        raise HTTPException(status_code=404, detail="Información no encontrada")
    return item


@router.post("/buildings", response_model=BuildingOut, status_code=status.HTTP_201_CREATED)
async def create_building(
    data: BuildingCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Building:
    building = Building(owner_id=user.id, org_id=user.org_id, name=data.name)
    session.add(building)
    await session.commit()
    await session.refresh(building)
    return building


@router.get("/buildings", response_model=list[BuildingOut])
async def list_buildings(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Building]:
    result = await session.execute(
        select(Building).where(Building.org_id == user.org_id).order_by(Building.id)
    )
    return list(result.scalars().all())


@router.post(
    "/buildings/{building_id}/knowledge",
    response_model=KnowledgeOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_building_knowledge(
    building_id: int,
    data: KnowledgeCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeItem:
    await get_owned_building(session, building_id, user)
    embedding = get_embedding_provider().embed([data.content])[0]
    item = KnowledgeItem(
        building_id=building_id,
        category=data.category,
        content=data.content,
        embedding=embedding,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/buildings/{building_id}/knowledge", response_model=list[KnowledgeOut])
async def list_building_knowledge(
    building_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[KnowledgeItem]:
    await get_owned_building(session, building_id, user)
    result = await session.execute(
        select(KnowledgeItem)
        .where(KnowledgeItem.building_id == building_id)
        .order_by(KnowledgeItem.id)
    )
    return list(result.scalars().all())


@router.patch(
    "/buildings/{building_id}/knowledge/{item_id}", response_model=KnowledgeOut
)
async def update_building_knowledge(
    building_id: int,
    item_id: int,
    data: KnowledgeUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeItem:
    item = await _owned_building_knowledge(session, building_id, item_id, user)
    if data.category is not None:
        item.category = data.category
    if data.content is not None and data.content != item.content:
        item.content = data.content
        item.embedding = get_embedding_provider().embed([data.content])[0]
    await session.commit()
    await session.refresh(item)
    return item


@router.delete(
    "/buildings/{building_id}/knowledge/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_building_knowledge(
    building_id: int,
    item_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    item = await _owned_building_knowledge(session, building_id, item_id, user)
    await session.delete(item)
    await session.commit()


@router.delete("/buildings/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_building(
    building_id: int,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> None:
    building = await get_owned_building(session, building_id, user)
    # Desvincular los pisos para no romper su FK; el conocimiento compartido cae en cascada.
    for prop in list(await _building_properties(session, building_id)):
        prop.building_id = None
    await session.delete(building)
    await session.commit()


async def _building_properties(session: AsyncSession, building_id: int):
    from app.models import Property

    result = await session.execute(select(Property).where(Property.building_id == building_id))
    return result.scalars().all()
