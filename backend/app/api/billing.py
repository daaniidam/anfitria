"""Facturación y planes: ver el plan, el uso y cambiarlo (pago simulado)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user, require_owner
from app.models import Organization, Property, User
from app.schemas import BillingStatus, PlanOut, PlanSelect
from app.services import plans

router = APIRouter(prefix="/billing", tags=["billing"])


async def _properties_used(session: AsyncSession, org_id: int | None) -> int:
    result = await session.execute(
        select(func.count()).select_from(Property).where(Property.org_id == org_id)
    )
    return int(result.scalar_one() or 0)


async def _status(session: AsyncSession, user: User) -> BillingStatus:
    org = await session.get(Organization, user.org_id)
    plan_id = org.plan if org else "free"
    plan = plans.get_plan(plan_id)
    used = await _properties_used(session, user.org_id)
    return BillingStatus(
        plan=plan["id"],
        plan_name=plan["name"],
        price_eur=plan["price_eur"],
        max_properties=plan["max_properties"],
        properties_used=used,
        plans=[
            PlanOut(
                id=p["id"], name=p["name"], price_eur=p["price_eur"],
                max_properties=p["max_properties"], current=p["id"] == plan_id,
            )
            for p in plans.PLANS
        ],
    )


@router.get("", response_model=BillingStatus)
async def billing_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BillingStatus:
    return await _status(session, user)


@router.post("/plan", response_model=BillingStatus)
async def set_plan(
    data: PlanSelect,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> BillingStatus:
    org = await session.get(Organization, user.org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    # No se puede bajar a un plan que no cubre los pisos que ya tienes.
    used = await _properties_used(session, user.org_id)
    if used > plans.max_properties(data.plan):
        raise HTTPException(
            status_code=400,
            detail=f"Tienes {used} pisos; ese plan permite {plans.max_properties(data.plan)}. "
            "Quita pisos o elige un plan mayor.",
        )
    org.plan = data.plan  # pago simulado: se activa el plan
    await session.commit()
    return await _status(session, user)
