"""Organización y equipo: varios usuarios comparten la misma cartera de pisos."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user, require_owner
from app.models import Organization, User
from app.schemas import MemberCreate, MemberRoleUpdate, OrgOut, UserOut
from app.security import hash_password

router = APIRouter(prefix="/org", tags=["org"])


async def _org_member(session: AsyncSession, member_id: int, org_id: int | None) -> User:
    member = await session.get(User, member_id)
    if member is None or member.org_id != org_id:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")
    return member


async def _count_owners(session: AsyncSession, org_id: int | None) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(User)
        .where(User.org_id == org_id, User.role == "owner")
    )
    return int(result.scalar_one() or 0)


@router.get("", response_model=OrgOut)
async def get_org(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Organization:
    org = await session.get(Organization, user.org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    return org


@router.get("/members", response_model=list[UserOut])
async def list_members(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[User]:
    result = await session.execute(
        select(User).where(User.org_id == user.org_id).order_by(User.id)
    )
    return list(result.scalars().all())


@router.post("/members", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def invite_member(
    data: MemberCreate,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> User:
    existing = await session.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    member = User(
        email=data.email,
        name=data.name,
        password_hash=hash_password(data.password),
        org_id=user.org_id,
        role=data.role,
    )
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


@router.patch("/members/{member_id}", response_model=UserOut)
async def update_member_role(
    member_id: int,
    data: MemberRoleUpdate,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> User:
    member = await _org_member(session, member_id, user.org_id)
    # No dejar la organización sin ningún propietario.
    if member.role == "owner" and data.role != "owner" and await _count_owners(
        session, user.org_id
    ) <= 1:
        raise HTTPException(status_code=400, detail="Debe quedar al menos un propietario")
    member.role = data.role
    await session.commit()
    await session.refresh(member)
    return member


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: int,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> None:
    if member_id == user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    member = await _org_member(session, member_id, user.org_id)
    await session.delete(member)
    await session.commit()
