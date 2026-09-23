"""Autenticación del anfitrión (cookies httpOnly + refresco + revocación)."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import ACCESS_COOKIE, get_current_user
from app.models import User
from app.ratelimit import limiter
from app.schemas import LoginRequest, TokenOut, UserCreate, UserOut
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _set_auth_cookies(response: Response, user: User) -> str:
    """Emite access + refresh en cookies httpOnly y devuelve el access token."""
    settings = get_settings()
    access = create_access_token(str(user.id), user.token_version)
    refresh = create_refresh_token(str(user.id), user.token_version)
    common = dict(httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    response.set_cookie(
        ACCESS_COOKIE, access, max_age=settings.access_token_expire_minutes * 60, **common
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh, max_age=settings.refresh_token_expire_minutes * 60, **common
    )
    return access


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request, data: UserCreate, session: AsyncSession = Depends(get_session)
) -> User:
    existing = await session.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    user = User(email=data.email, name=data.name, password_hash=hash_password(data.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenOut:
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    access = _set_auth_cookies(response, user)
    return TokenOut(access_token=access)


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    request: Request, response: Response, session: AsyncSession = Depends(get_session)
) -> TokenOut:
    token = request.cookies.get(REFRESH_COOKIE)
    payload = decode_token(token, expected_type="refresh") if token else None
    if payload is None:
        raise HTTPException(status_code=401, detail="Sesión caducada")
    user = await session.get(User, int(payload["sub"]))
    if user is None or payload.get("tv") != user.token_version:
        raise HTTPException(status_code=401, detail="Sesión caducada")
    access = _set_auth_cookies(response, user)
    return TokenOut(access_token=access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    # Revoca todos los tokens previos (incrementa token_version) y borra las cookies.
    user.token_version += 1
    await session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE)
    return response


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
