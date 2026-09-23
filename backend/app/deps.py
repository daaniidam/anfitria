"""Dependencias comunes (autenticación).

El token de acceso viaja preferentemente en una cookie httpOnly (resiste XSS),
pero también se acepta en la cabecera `Authorization: Bearer` para API/curl/tests.
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.security import decode_token

ACCESS_COOKIE = "access_token"
CSRF_COOKIE = "csrf_token"


def _token_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(ACCESS_COOKIE)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = _token_from_request(request)
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado"
    )
    if not token:
        raise unauthorized
    payload = decode_token(token, expected_type="access")
    if payload is None:
        raise unauthorized
    user = await session.get(User, int(payload["sub"]))
    if user is None or payload.get("tv") != user.token_version:
        # Usuario inexistente o token revocado (token_version incrementado).
        raise unauthorized
    return user


async def require_owner(user: User = Depends(get_current_user)) -> User:
    """Solo el propietario (owner) de la org puede gestionar el equipo y borrar pisos."""
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Solo el propietario puede hacer esto")
    return user
