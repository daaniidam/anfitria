"""Integraciones con PMS / Channel Manager: conectar y sincronizar la cartera."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user, require_owner
from app.models import Integration, Property, Reservation, User
from app.schemas import IntegrationProvider, PMSSyncResult
from app.services import pms

router = APIRouter(prefix="/integrations", tags=["integrations"])


async def _get_integration(
    session: AsyncSession, org_id: int | None, provider: str
) -> Integration | None:
    result = await session.execute(
        select(Integration).where(
            Integration.org_id == org_id, Integration.provider == provider
        )
    )
    return result.scalar_one_or_none()


@router.get("", response_model=list[IntegrationProvider])
async def list_integrations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[IntegrationProvider]:
    rows = await session.execute(
        select(Integration).where(Integration.org_id == user.org_id)
    )
    by_provider = {i.provider: i for i in rows.scalars().all()}
    out: list[IntegrationProvider] = []
    for p in pms.PROVIDERS:
        integ = by_provider.get(p["id"])
        connected = integ is not None and integ.status == "connected"
        out.append(
            IntegrationProvider(
                id=p["id"],
                name=p["name"],
                available=p["available"],
                connected=connected,
                account=integ.account if integ else None,
            )
        )
    return out


@router.post("/{provider}/connect", response_model=IntegrationProvider)
async def connect(
    provider: str,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> IntegrationProvider:
    meta = next((p for p in pms.PROVIDERS if p["id"] == provider), None)
    if meta is None or not meta["available"]:
        raise HTTPException(status_code=400, detail="Integración no disponible todavía")
    integ = await _get_integration(session, user.org_id, provider)
    if integ is None:
        integ = Integration(org_id=user.org_id, provider=provider, account=f"{provider}@demo")
        session.add(integ)
    integ.status = "connected"
    await session.commit()
    return IntegrationProvider(
        id=provider, name=meta["name"], available=True, connected=True, account=integ.account
    )


@router.post("/{provider}/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    provider: str,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> None:
    integ = await _get_integration(session, user.org_id, provider)
    if integ is not None:
        integ.status = "disconnected"
        await session.commit()


@router.post("/{provider}/sync", response_model=PMSSyncResult)
async def sync(
    provider: str,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> PMSSyncResult:
    integ = await _get_integration(session, user.org_id, provider)
    if integ is None or integ.status != "connected":
        raise HTTPException(status_code=400, detail="Conecta la integración primero")
    if not pms.is_available(provider):
        raise HTTPException(status_code=400, detail="Integración no disponible todavía")

    props, reservations = pms.fetch_portfolio(provider)

    # Upsert de pisos por external_ref (no duplica al resincronizar).
    ref_to_prop: dict[str, Property] = {}
    new_props = 0
    for p in props:
        existing = await session.execute(
            select(Property).where(
                Property.org_id == user.org_id, Property.external_ref == p["external_ref"]
            )
        )
        prop = existing.scalar_one_or_none()
        if prop is None:
            prop = Property(
                owner_id=user.id,
                org_id=user.org_id,
                name=p["name"],
                default_language=p["default_language"],
                external_ref=p["external_ref"],
            )
            session.add(prop)
            await session.flush()
            new_props += 1
        ref_to_prop[p["external_ref"]] = prop

    # Upsert de reservas por (piso, código).
    new_res = 0
    for r in reservations:
        prop = ref_to_prop.get(r["property_ref"])
        if prop is None:
            continue
        existing = await session.execute(
            select(Reservation).where(
                Reservation.property_id == prop.id, Reservation.code == r["code"]
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue
        session.add(
            Reservation(
                property_id=prop.id,
                guest_name=r["guest_name"],
                guest_ref=r["guest_ref"],
                check_in=r["check_in"],
                check_out=r["check_out"],
                source=r["source"],
                code=r["code"],
            )
        )
        new_res += 1

    await session.commit()
    return PMSSyncResult(properties_imported=new_props, reservations_imported=new_res)
