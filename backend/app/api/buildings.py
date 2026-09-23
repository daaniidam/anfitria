"""Edificios / grupos de pisos con conocimiento compartido."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.embeddings.factory import get_embedding_provider
from app.db import get_session
from app.deps import get_current_user
from app.models import Building, KnowledgeItem, User
from app.schemas import BuildingCreate, BuildingOut, KnowledgeCreate, KnowledgeOut

router = APIRouter(tags=["buildings"])


async def get_owned_building(session: AsyncSession, building_id: int, user: User) -> Building:
    building = await session.get(Building, building_id)
    if building is None or building.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")
    return building


@router.post("/buildings", response_model=BuildingOut, status_code=status.HTTP_201_CREATED)
async def create_building(
    data: BuildingCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Building:
    building = Building(owner_id=user.id, name=data.name)
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
        select(Building).where(Building.owner_id == user.id).order_by(Building.id)
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
