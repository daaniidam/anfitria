"""Hash de contraseñas y tokens JWT (acceso + refresco)."""
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.config import get_settings

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)


def _encode(subject: str, token_version: int, token_type: str, minutes: int) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=minutes)
    payload = {"sub": subject, "tv": token_version, "type": token_type, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, token_version: int = 0) -> str:
    return _encode(
        subject, token_version, "access", get_settings().access_token_expire_minutes
    )


def create_refresh_token(subject: str, token_version: int = 0) -> str:
    return _encode(
        subject, token_version, "refresh", get_settings().refresh_token_expire_minutes
    )


def decode_token(token: str, expected_type: str = "access") -> dict | None:
    """Devuelve el payload si el token es válido y del tipo esperado; si no, None."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload
