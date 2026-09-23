"""Autenticación del anfitrión (cookies httpOnly + refresco rotatorio + CSRF)."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import ACCESS_COOKIE, CSRF_COOKIE, get_current_user
from app.models import Organization, User
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


async def _issue_session(response: Response, user: User, session: AsyncSession) -> str:
    """Emite access + refresh (rotatorio) + CSRF en cookies y devuelve el access token."""
    settings = get_settings()
    jti = secrets.token_urlsafe(16)
    user.refresh_jti = jti
    await session.commit()

    access = create_access_token(str(user.id), user.token_version)
    refresh = create_refresh_token(str(user.id), user.token_version, jti=jti)
    csrf = secrets.token_urlsafe(24)
    secure = settings.cookie_secure
    samesite = settings.cookie_samesite
    response.set_cookie(
        ACCESS_COOKIE, access, max_age=settings.access_token_expire_minutes * 60,
        httponly=True, secure=secure, samesite=samesite,
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh, max_age=settings.refresh_token_expire_minutes * 60,
        httponly=True, secure=secure, samesite=samesite,
    )
    # CSRF: cookie legible por JS (no httpOnly). El frontend la reenvía como cabecera
    # X-CSRF-Token; el middleware comprueba que coinciden (patrón double-submit).
    response.set_cookie(
        CSRF_COOKIE, csrf, max_age=settings.access_token_expire_minutes * 60,
        httponly=False, secure=secure, samesite=samesite,
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
    # Al registrarse se crea su organización y el usuario es el propietario (owner).
    org = Organization(name=data.name)
    session.add(org)
    await session.flush()
    user = User(
        email=data.email,
        name=data.name,
        password_hash=hash_password(data.password),
        org_id=org.id,
        role="owner",
    )
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
    access = await _issue_session(response, user, session)
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
    # Rotación de un solo uso: el jti debe ser el último emitido. Un refresh viejo
    # (ya rotado o robado y reusado) queda invalidado.
    if (
        user is None
        or payload.get("tv") != user.token_version
        or payload.get("jti") != user.refresh_jti
    ):
        raise HTTPException(status_code=401, detail="Sesión caducada")
    access = await _issue_session(response, user, session)
    return TokenOut(access_token=access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    # Revoca todos los tokens previos (incrementa token_version, borra el refresh jti).
    user.token_version += 1
    user.refresh_jti = None
    await session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE)
    response.delete_cookie(CSRF_COOKIE)
    return response


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
