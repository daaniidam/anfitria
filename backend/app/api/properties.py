"""Pisos y su ficha de conocimiento."""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.embeddings.factory import get_embedding_provider
from app.db import get_session
from app.deps import get_current_user, require_owner
from app.models import KnowledgeItem, Organization, Property, User
from app.schemas import (
    KnowledgeCreate,
    KnowledgeImportOut,
    KnowledgeOut,
    KnowledgeUpdate,
    PropertyCreate,
    PropertyOut,
    PropertyUpdate,
)
from app.services import plans
from app.services.import_knowledge import parse_upload

MAX_IMPORT_BYTES = 5_000_000  # 5 MB

router = APIRouter(tags=["properties"])


async def get_owned_property(session: AsyncSession, property_id: int, user: User) -> Property:
    prop = await session.get(Property, property_id)
    if prop is None or prop.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Piso no encontrado")
    return prop


async def _owned_property_knowledge(
    session: AsyncSession, property_id: int, item_id: int, user: User
) -> KnowledgeItem:
    await get_owned_property(session, property_id, user)
    item = await session.get(KnowledgeItem, item_id)
    if item is None or item.property_id != property_id:
        raise HTTPException(status_code=404, detail="Información no encontrada")
    return item


@router.post("/properties", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
async def create_property(
    data: PropertyCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Property:
    if data.building_id is not None:
        from app.api.buildings import get_owned_building

        await get_owned_building(session, data.building_id, user)

    # Límite del plan (paywall).
    org = await session.get(Organization, user.org_id)
    used = int(
        (
            await session.execute(
                select(func.count()).select_from(Property).where(Property.org_id == user.org_id)
            )
        ).scalar_one()
        or 0
    )
    if used >= plans.max_properties(org.plan if org else "free"):
        raise HTTPException(
            status_code=402,
            detail="Has alcanzado el límite de pisos de tu plan. Mejóralo en Facturación.",
        )

    prop = Property(
        owner_id=user.id,
        org_id=user.org_id,
        name=data.name,
        address=data.address,
        default_language=data.default_language,
        auto_answer=data.auto_answer,
        auto_answer_threshold=data.auto_answer_threshold,
        whatsapp_phone_number_id=data.whatsapp_phone_number_id,
        building_id=data.building_id,
    )
    session.add(prop)
    await session.commit()
    await session.refresh(prop)
    return prop


@router.get("/properties", response_model=list[PropertyOut])
async def list_properties(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Property]:
    result = await session.execute(
        select(Property)
        .where(Property.org_id == user.org_id)
        .order_by(Property.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.patch("/properties/{property_id}", response_model=PropertyOut)
async def update_property(
    property_id: int,
    data: PropertyUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Property:
    prop = await get_owned_property(session, property_id, user)
    for field_name, value in data.model_dump(exclude_unset=True).items():
        setattr(prop, field_name, value)
    await session.commit()
    await session.refresh(prop)
    return prop


@router.delete("/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: int,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> None:
    prop = await get_owned_property(session, property_id, user)
    await session.delete(prop)
    await session.commit()


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


@router.post(
    "/properties/{property_id}/knowledge/import",
    response_model=KnowledgeImportOut,
    status_code=status.HTTP_201_CREATED,
)
async def import_knowledge(
    property_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeImportOut:
    """Importa la ficha desde un CSV (categoría, contenido) o un PDF (se trocea)."""
    await get_owned_property(session, property_id, user)
    data = await file.read()
    if len(data) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="El fichero es demasiado grande (máx. 5 MB)")
    try:
        pairs = parse_upload(file.filename or "", file.content_type, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not pairs:
        raise HTTPException(status_code=400, detail="No se encontró contenido para importar")

    embeddings = get_embedding_provider().embed([content for _, content in pairs])
    for (category, content), embedding in zip(pairs, embeddings, strict=True):
        session.add(
            KnowledgeItem(
                property_id=property_id,
                category=category,
                content=content,
                embedding=embedding,
            )
        )
    await session.commit()
    return KnowledgeImportOut(imported=len(pairs))


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


@router.patch(
    "/properties/{property_id}/knowledge/{item_id}", response_model=KnowledgeOut
)
async def update_knowledge(
    property_id: int,
    item_id: int,
    data: KnowledgeUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeItem:
    item = await _owned_property_knowledge(session, property_id, item_id, user)
    if data.category is not None:
        item.category = data.category
    if data.content is not None and data.content != item.content:
        item.content = data.content
        item.embedding = get_embedding_provider().embed([data.content])[0]
    await session.commit()
    await session.refresh(item)
    return item


@router.delete(
    "/properties/{property_id}/knowledge/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_knowledge(
    property_id: int,
    item_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    item = await _owned_property_knowledge(session, property_id, item_id, user)
    await session.delete(item)
    await session.commit()
